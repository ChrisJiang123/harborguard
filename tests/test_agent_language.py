"""English output safety, facts and retained Chinese compatibility."""
import asyncio
import json
import time
from dataclasses import replace
import pytest
from agent.config import load_settings
from agent.context import context_ids
from agent.factcheck import check_draft_facts
from agent.language import CJK, text_errors
from agent.router import Router
from agent.schemas import DraftOutputError, RecommendationDraft, parse_model_draft, validate_draft
from agent.template import generate_recommendation, generate_answer
from ml.lora.gen_contexts import generate_contexts


@pytest.fixture(autouse=True)
def english(monkeypatch):
    monkeypatch.setenv("AGENT_LANG", "en")


def test_default_language_and_invalid_configuration(monkeypatch):
    monkeypatch.delenv("AGENT_LANG")
    assert load_settings().agent_lang == "en"
    monkeypatch.setenv("AGENT_LANG", "fr")
    with pytest.raises(ValueError, match="AGENT_LANG"):
        load_settings()


def test_templates_keep_facts_and_ids_for_all_context_kinds():
    contexts = generate_contexts(100, 42)
    for context in contexts:
        draft = generate_recommendation(context)
        assert not text_errors(draft), draft
        assert not validate_draft(draft, context_ids(context), {o['id'] for o in context.get('options', [])})
        result = check_draft_facts(draft, context)
        assert result.ok, (context, draft, result.errors)
    assert {c['kind'] for c in contexts} == {'security', 'buoy', 'disaster'}


def test_unknown_contact_and_question_do_not_echo_raw_class_or_chinese():
    c = next(c for c in generate_contexts(30, 7) if c['kind']=='security')
    c['options']=[]; c['ranked']=[]; c['track']['cls']='unknown'
    d = generate_recommendation(c)
    assert 'unidentified contact' in d.summary
    assert 'unknown' not in d.summary
    answer = generate_answer('中文问题', track=c['track'], state={'alerts':[]})
    assert not CJK.search(answer)


@pytest.mark.parametrize('field', ['summary', 'explanation', 'uncertainties'])
def test_cjk_is_rejected_even_after_the_truncation_boundary(field):
    p = dict(summary='Review contact', explanation='Review the contact.', uncertainties=[],
             evidence_ids=[], recommended_option_id=None, confidence='low')
    p[field] = ['Review 中文'] if field=='uncertainties' else 'Review '*310+'中文'
    with pytest.raises(DraftOutputError, match='CJK'):
        parse_model_draft(json.dumps(p,ensure_ascii=False),set(),set())


def test_lengths_use_words_in_english_and_characters_in_chinese(monkeypatch):
    d = RecommendationDraft(summary='word '*25, explanation='word '*120,
        uncertainties=['word '*15], recommended_option_id=None, evidence_ids=[], confidence='low')
    assert not text_errors(d)
    assert text_errors(d.model_copy(update={'summary':'word '*26}))
    monkeypatch.setenv('AGENT_LANG','zh')
    assert text_errors(d)
    assert not text_errors(d.model_copy(update={'summary':'字'*60,'explanation':'字'*300,'uncertainties':['字'*40]}))


def test_chinese_lora_output_falls_back_without_counting_model_success(tmp_path):
    from tests.test_agent_phase2 import FakeProvider, sample_context, valid_payload
    async def run():
        cfg=replace(load_settings(),cloud_provider='disabled',agent_failure_log=str(tmp_path/'facts.jsonl'))
        local=FakeProvider('ollama','harborguard-lora',[json.dumps(valid_payload(),ensure_ascii=False)]*2)
        router=Router(cfg,local=local)
        try:
            result=await router.generate(sample_context('offline'),deadline=time.perf_counter()+3)
            assert result.model=='template'
            assert local.calls and len(local.calls)==2
            assert router.stats['providers']['local']['success']==0
            assert router.stats['template_fallbacks']==1
            assert router.stats['providers']['cloud']['draft_attempts']==0
            assert not text_errors(result.draft)
        finally:
            await router.aclose()
    asyncio.run(run())


def test_english_numeric_contradictions_and_missing_uncertainties_are_rejected():
    from tests.test_agent_phase3 import context
    ctx=context()
    good=generate_recommendation(ctx)
    assert check_draft_facts(good,ctx).ok
    for sentence in ['1 buoy covers.', 'Confidence 0.40.', 'Residual risk 0.7.', 'Delay 9 hours.', 'B1 is offline.']:
        assert not check_draft_facts(good.model_copy(update={'explanation':sentence}),ctx).ok, sentence
    weak=context(buoys={'down':['B1','B2'],'covering_track':['B3']})
    d=generate_recommendation(weak)
    assert check_draft_facts(d,weak).ok
    assert not check_draft_facts(d.model_copy(update={'uncertainties':[]}),weak).ok


def test_zh_preserves_original_checks_for_english_looking_terms(monkeypatch):
    from tests.test_agent_phase3 import context, draft
    monkeypatch.setenv("AGENT_LANG", "zh")
    bad = draft(summary="核查 unknown 目标", explanation="unknown 目标相关，B1 浮标离线。")
    result = check_draft_facts(bad, context())
    assert any("离线列表为空" in error for error in result.errors)
