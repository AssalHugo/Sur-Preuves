"""Core LLM client orchestrator with budget enforcement, caching, and batch routing."""

import logging
import uuid
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from csc.config import settings
from csc.contracts.enums import LlmTier
from csc.contracts.uuid_v7 import uuid7
from csc.db.models import LlmCallModel
from csc.llm.budget import budget_manager
from csc.llm.cache import local_cache
from csc.llm.exceptions import (
    LlmError,
    RealtimeDisallowedError,
    StructuredOutputError,
)
from csc.llm.guardrails import validate_free_tier
from csc.llm.models_config import RoleConfig, models_config_manager
from csc.llm.pricing import pricing_registry
from csc.llm.prompts import prompt_manager
from csc.llm.providers.base import BatchItem, ProviderResponse
from csc.llm.providers.registry import provider_registry

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BatchJob(BaseModel):
    """Metadata representing an asynchronous batch job."""

    id: str
    job_id: str
    prompt_id: str
    model: str
    role: str
    tier: str
    item_count: int
    deferred_count: int = 0


class LlmClient:
    """Unified entry point for LLM inference calls."""

    def __init__(self) -> None:
        pass

    async def run(
        self,
        prompt_id: str,
        variables: dict[str, Any],
        output_model: type[T],
        role: str = "extraction",
        tier: str = "paid",
        debug: bool = False,
        is_public: bool = False,
        synth_model: str | None = None,
        session: Session | None = None,
    ) -> T:
        """Execute a single structured generation call with strict budget and privacy controls.

        Paid tier requires debug=True or settings.llm_debug=True for realtime calls.
        """
        tier_norm = tier.lower()
        cfg = models_config_manager.get_config()
        role_cfg = cfg.roles.get(role)
        if role_cfg is None:
            raise LlmError(f"Role '{role}' is not configured in models.yaml.")

        provider_name = role_cfg.provider
        model = role_cfg.model

        # Handle cross-verification routing
        same_provider = False
        if role == "verification":
            s_model = synth_model or cfg.roles.get("synthesis", role_cfg).model
            v_prov, v_model = models_config_manager.pick_verifier(s_model, cfg)
            provider_name = v_prov
            model = v_model
            same_provider = v_prov == cfg.roles.get("synthesis", role_cfg).provider

        # Tier guardrails
        if tier_norm == LlmTier.FREE.value:
            validate_free_tier(model=model, variables=variables, is_public=is_public)
        elif tier_norm == LlmTier.PAID.value:
            is_debug_allowed = debug or settings.llm_debug
            if not is_debug_allowed:
                raise RealtimeDisallowedError(
                    "Realtime execution is disallowed for tier='paid'. "
                    "Use submit_batch() for production or pass debug=True for local testing."
                )

        # Render prompt template
        rendered_prompt, prompt_version, prompt_sha = prompt_manager.render(prompt_id, variables)

        params: dict[str, Any] = {
            "temperature": role_cfg.temperature,
            "max_output_tokens": role_cfg.max_output_tokens,
        }
        if role_cfg.thinking:
            params["thinking"] = role_cfg.thinking
        if same_provider:
            params["same_provider"] = True

        # Check local cache
        cache_key = local_cache.compute_key(
            prompt_sha=prompt_sha,
            model=model,
            params=params,
            variables=variables,
        )
        cached_entry = local_cache.get(cache_key)
        if cached_entry is not None:
            logger.debug("Local cache hit for key %s", cache_key)
            try:
                parsed_cached = output_model.model_validate_json(cached_entry.raw_output)
                return parsed_cached
            except Exception as e:
                logger.warning("Cached entry invalid for model %s: %s", output_model.__name__, e)

        # Count tokens and estimate cost
        provider = provider_registry.get(provider_name)
        input_tokens = await provider.count_tokens(model, rendered_prompt)
        estimated_cost = pricing_registry.estimate_call_cost(
            model=model,
            input_tokens=input_tokens,
            max_output_tokens=role_cfg.max_output_tokens,
            is_batch=False,
            tier=tier_norm,
        )

        # Budget pre-check
        budget_manager.check_budget(estimated_cost=estimated_cost, session=session)

        # Execute generation with 1 retry on invalid structured output
        max_attempts = 2
        response: ProviderResponse | None = None
        parsed_result: T | None = None

        for attempt in range(max_attempts):
            response = await provider.generate(
                model=model,
                prompt=rendered_prompt,
                schema=output_model,
                params=params,
                tier=tier_norm,
            )
            try:
                parsed_result = output_model.model_validate_json(response.raw_output)
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise StructuredOutputError(
                        f"Structured output parsing failed after {max_attempts} attempts: {e}"
                    ) from e
                logger.warning(
                    "Structured output invalid (attempt %d/%d). Retrying...",
                    attempt + 1,
                    max_attempts,
                )

        assert response is not None
        assert parsed_result is not None

        # Calculate actual cost and reconcile
        actual_cost = pricing_registry.calculate_cost(
            model=model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cached_tokens=response.cached_tokens,
            thinking_tokens=response.thinking_tokens,
            is_batch=False,
            tier=tier_norm,
        )
        budget_manager.reconcile(estimated_cost=estimated_cost, actual_cost=actual_cost)

        # Update cache
        local_cache.set(
            key=cache_key,
            raw_output=response.raw_output,
            input_tokens=response.input_tokens,
            cached_tokens=response.cached_tokens,
            output_tokens=response.output_tokens,
            thinking_tokens=response.thinking_tokens,
            latency_ms=response.latency_ms,
        )

        # Record spend
        budget_manager.record_spend(
            cost_usd=actual_cost,
            role=role,
            model=model,
        )

        # Persist audit record in DB if session is active
        if session is not None:
            try:
                call_id = uuid7()
                call_record = LlmCallModel(
                    id=call_id,
                    prompt_id=prompt_id,
                    prompt_version=prompt_version,
                    prompt_sha=prompt_sha,
                    provider=provider_name,
                    model=model,
                    tier=tier_norm,
                    batch_job_id=None,
                    params=params,
                    input_tokens=response.input_tokens,
                    cached_tokens=response.cached_tokens,
                    output_tokens=response.output_tokens,
                    thinking_tokens=response.thinking_tokens,
                    cost_usd=actual_cost,
                    latency_ms=response.latency_ms,
                    raw_output=response.raw_output,
                )
                session.add(call_record)
                session.commit()
            except Exception as e:
                logger.warning("Failed to record LlmCallModel in database: %s", e)
                session.rollback()

        return parsed_result

    async def submit_batch(
        self,
        prompt_id: str,
        items: list[dict[str, Any]],
        output_model: type[T],
        role: str = "extraction",
        tier: str = "paid",
        is_public: bool = False,
        split_if_needed: bool = False,
        synth_model: str | None = None,
        session: Session | None = None,
    ) -> BatchJob:
        """Submit a batch generation job under strict budget and privacy controls."""
        tier_norm = tier.lower()
        cfg = models_config_manager.get_config()
        role_cfg = cfg.roles.get(role)
        if role_cfg is None:
            raise LlmError(f"Role '{role}' is not configured in models.yaml.")

        provider_name = role_cfg.provider
        model = role_cfg.model

        same_provider = False
        if role == "verification":
            s_model = synth_model or cfg.roles.get("synthesis", role_cfg).model
            v_prov, v_model = models_config_manager.pick_verifier(s_model, cfg)
            provider_name = v_prov
            model = v_model
            same_provider = v_prov == cfg.roles.get("synthesis", role_cfg).provider

        # Guardrails for all items
        if tier_norm == LlmTier.FREE.value:
            for item in items:
                validate_free_tier(model=model, variables=item, is_public=is_public)

        # Render prompts for items
        batch_items: list[BatchItem] = []
        for idx, item_vars in enumerate(items):
            c_id = item_vars.get("id", f"item_{idx}_{uuid.uuid4().hex[:6]}")
            rendered, _, _ = prompt_manager.render(prompt_id, item_vars)
            batch_items.append(BatchItem(custom_id=str(c_id), prompt=rendered))

        # Estimate item cost
        provider = provider_registry.get(provider_name)
        sample_prompt = batch_items[0].prompt if batch_items else ""
        sample_tokens = await provider.count_tokens(model, sample_prompt) if sample_prompt else 100
        single_cost = pricing_registry.estimate_call_cost(
            model=model,
            input_tokens=sample_tokens,
            max_output_tokens=role_cfg.max_output_tokens,
            is_batch=True,
            tier=tier_norm,
        )

        admitted_items = batch_items
        deferred_count = 0
        if split_if_needed:
            admitted_items, deferred = budget_manager.split_batch_to_fit(
                batch_items, item_cost=single_cost, session=session
            )
            deferred_count = len(deferred)
        else:
            total_est = single_cost * len(batch_items)
            budget_manager.check_budget(estimated_cost=total_est, session=session)

        params: dict[str, Any] = {
            "temperature": role_cfg.temperature,
            "max_output_tokens": role_cfg.max_output_tokens,
        }
        if role_cfg.thinking:
            params["thinking"] = role_cfg.thinking
        if same_provider:
            params["same_provider"] = True

        raw_job_id = await provider.submit_batch(
            model=model,
            items=admitted_items,
            schema=output_model,
            params=params,
            tier=tier_norm,
        )

        return BatchJob(
            id=str(uuid.uuid4()),
            job_id=raw_job_id,
            prompt_id=prompt_id,
            model=model,
            role=role,
            tier=tier_norm,
            item_count=len(admitted_items),
            deferred_count=deferred_count,
        )

    async def collect_batch(
        self,
        job_id: str,
        output_model: type[T],
        role: str = "extraction",
        tier: str = "paid",
        provider_name: str = "google",
        session: Session | None = None,
    ) -> list[T]:
        """Fetch completed batch outputs, validate against schema, and record costs."""
        tier_norm = tier.lower()
        cfg = models_config_manager.get_config()
        role_cfg = cfg.roles.get(role, RoleConfig(model="gemini-3.5-flash-lite"))
        model = role_cfg.model

        provider = provider_registry.get(provider_name)
        responses = await provider.collect_batch(job_id)

        results: list[T] = []
        for resp in responses:
            parsed = output_model.model_validate_json(resp.raw_output)
            results.append(parsed)

            cost = pricing_registry.calculate_cost(
                model=model,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                cached_tokens=resp.cached_tokens,
                thinking_tokens=resp.thinking_tokens,
                is_batch=True,
                tier=tier_norm,
            )
            budget_manager.record_spend(cost_usd=cost, role=role, model=model)

            if session is not None:
                try:
                    record = LlmCallModel(
                        id=uuid7(),
                        prompt_id=role,
                        prompt_version="1.0.0",
                        prompt_sha="batch",
                        provider=provider_name,
                        model=model,
                        tier=tier_norm,
                        batch_job_id=job_id,
                        params={},
                        input_tokens=resp.input_tokens,
                        cached_tokens=resp.cached_tokens,
                        output_tokens=resp.output_tokens,
                        thinking_tokens=resp.thinking_tokens,
                        cost_usd=cost,
                        latency_ms=resp.latency_ms,
                        raw_output=resp.raw_output,
                    )
                    session.add(record)
                    session.commit()
                except Exception:
                    session.rollback()

        return results


llm = LlmClient()
