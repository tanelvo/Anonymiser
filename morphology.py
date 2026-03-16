import importlib
from estnltk import Text
from estnltk.taggers import VabamorfTagger


# Map Vabamorf form tags to Estonian case names used by anonymiser.py
_FORM_TO_CASE = {
    "n": "Nom", # Nimetav (Kes? Mis?)
    "g": "Gen", # Omastav (Kelle? Mille?)
    "p": "Par", # Osastav (Keda? Mida?)
    "ill": "Ill", # Sisseütlev (Kellesse? Millesse? Kuhu?)
    "in": "Ine", # Seesütlev (Kelles? Milles? Kus?)
    "el": "Ela", # Seestütlev (Kellest? Millest? Kust?)
    "all": "All", # AlaleÜtlev (Kellele? Millele? Kuhu?)
    "ad": "Ade", # Alalütlev (Kellel? Millel? Lis?)
    "abl": "Abl", # Alaltütlev (Kellelt? Millelt? Kust?)
    "tr": "Tra", # Saav (Kelleks? Milleks?)
    "ter": "Ter", # Rajav (Kelleni? Milleni?)
    "es": "Ess", # Olev (Kellena? Millena?)
    "kom": "Com", # Ilmaütlev (Kelleta? Milleta?)
    "ab": "Abe", # Kaasaütlev (Kellega? Millega?)
}
_CASE_TO_FORM = {
    "Nom": "sg n",
    "Gen": "sg g",
    "Par": "sg p",
    "Ill": "sg ill",
    "Ine": "sg in",
    "Ela": "sg el",
    "All": "sg all",
    "Ade": "sg ad",
    "Abl": "sg abl",
    "Tra": "sg tr",
    "Ter": "sg ter",
    "Ess": "sg es",
    "Com": "sg kom",
    "Abe": "sg ab",
}


def _case_from_form(form):
    """
    Extract Case=... from a Vabamorf form string (e.g. "sg n", "pl g").
    """
    if not form:
        return None
    parts = str(form).split()
    if not parts:
        return None
    # Case is the last token in form (e.g. "n", "g", "ill", "kom")
    case_key = parts[-1]
    return _FORM_TO_CASE.get(case_key)


def _get_morph_layer(text_obj):
    """
    Try tagging the text with Vabamorf via EstNLTK and return the morph layer.
    """
    if VabamorfTagger is not None:
        try:
            VabamorfTagger().tag(text_obj)
            if "morph_analysis" in text_obj.layers:
                return text_obj["morph_analysis"]
        except Exception:
            pass

    try:
        text_obj.tag_layer(["morph_analysis"])
        if "morph_analysis" in text_obj.layers:
            return text_obj["morph_analysis"]
    except Exception:
        pass

    return None


def analyze_morphology(text):
    """
    Analyze text and return a list of dicts with a "feats" key containing Case=...
    """
    if not text:
        return []

    if Text is None:
        raise ImportError("estnltk is required for morphology analysis")

    text_obj = Text(text)
    morph_layer = _get_morph_layer(text_obj)
    if morph_layer is None:
        return []

    analyses = []
    for span in morph_layer:
        ann = None
        if hasattr(span, "annotations") and span.annotations:
            ann = span.annotations[0]
        elif hasattr(span, "analysis") and span.analysis:
            ann = span.analysis[0]
        elif isinstance(span, dict):
            ann = span

        if not ann:
            continue

        form = None
        if isinstance(ann, dict):
            form = ann.get("form") or ann.get("form_name")
        else:
            form = getattr(ann, "form", None)

        case = _case_from_form(form)
        if case:
            analyses.append({"feats": f"Case={case}"})

    # Log raw forms and derived cases for debugging
    print("========================================")
    print(f"[morphology] text='{text}' analyses={analyses}")
    return analyses


def _extract_case_code_from_feats(feats):
    if not feats or "Case=" not in feats:
        return ""
    for part in feats.split("|"):
        if part.startswith("Case="):
            return part.split("=", 1)[1]
    return ""


def _synthesize_last_token_only(text, target_form):
    """
    Apply morphology only to the last token of a multi-word string.
    """
    if not text or not target_form:
        return ""

    parts = [p for p in str(text).split() if p]
    if not parts:
        return ""

    if len(parts) == 1:
        candidates = synthesize_with_vabamorf(parts[0], target_form) or []
        return candidates[0] if candidates else ""

    prefix = " ".join(parts[:-1])
    last = parts[-1]
    candidates = synthesize_with_vabamorf(last, target_form) or []
    if not candidates:
        return ""
    return f"{prefix} {candidates[0]}"


def to_nominative(text):
    """
    Best-effort conversion of a name to nominative using EstNLTK morphology.
    If analysis is unavailable, returns the original text.
    """
    if not text:
        return text

    try:
        text_obj = Text(text)
        morph_layer = _get_morph_layer(text_obj)
        if morph_layer is None:
            return text
        if "words" not in text_obj.layers:
            text_obj.tag_layer(["words"])
        words_layer = text_obj["words"]
    except Exception:
        return text

    if len(morph_layer) != len(words_layer):
        return text

    tokens = []
    for i, word in enumerate(words_layer):
        lemma = None
        span = morph_layer[i]
        ann = None
        if hasattr(span, "annotations") and span.annotations:
            ann = span.annotations[0]
        elif hasattr(span, "analysis") and span.analysis:
            ann = span.analysis[0]
        elif isinstance(span, dict):
            ann = span

        if isinstance(ann, dict):
            lemma = ann.get("lemma") or ann.get("root")
            if not lemma and ann.get("root_tokens"):
                lemma = ann.get("root_tokens")[0]
        else:
            lemma = getattr(ann, "lemma", None)

        tokens.append(lemma or word.text)

    result_tokens = []
    join_next = False
    for tok in tokens:
        if tok == "-":
            if result_tokens:
                result_tokens[-1] = result_tokens[-1] + "-"
                join_next = True
            continue
        if join_next and result_tokens:
            result_tokens[-1] = result_tokens[-1] + tok
            join_next = False
        else:
            result_tokens.append(tok)

    return " ".join(result_tokens)


def analyze_text_morphology(text, target_case=None, combine_words=False):
    """
    Return per-token morphology info:
    - token: original surface form
    - case: grammatical case (if available)
    - nominative: lemma/root-based nominative fallback
    """
    if not text:
        return []

    if combine_words:
        nominative_text = to_nominative(text)
        cases = []
        for item in analyze_morphology(text):
            case_code = _extract_case_code_from_feats(item.get("feats", ""))
            if case_code:
                cases.append(case_code)
        unified_case = cases[0] if cases and len(set(cases)) == 1 else ""
        target_value = ""
        if target_case:
            target_form = _CASE_TO_FORM.get(target_case)
            if target_form:
                target_value = _synthesize_last_token_only(nominative_text or text, target_form)
                if not target_value:
                    target_value = _synthesize_last_token_only(text, target_form)

        return [{
            "token": text,
            "case": unified_case,
            "nominative": nominative_text or text,
            "target_case_value": target_value
        }]

    if Text is None:
        raise ImportError("estnltk is required for morphology analysis")

    try:
        text_obj = Text(text)
        morph_layer = _get_morph_layer(text_obj)
        if morph_layer is None:
            return []
        if "words" not in text_obj.layers:
            text_obj.tag_layer(["words"])
        words_layer = text_obj["words"]
    except Exception:
        return []

    results = []
    size = min(len(morph_layer), len(words_layer))
    for i in range(size):
        word = words_layer[i]
        span = morph_layer[i]
        ann = None
        if hasattr(span, "annotations") and span.annotations:
            ann = span.annotations[0]
        elif hasattr(span, "analysis") and span.analysis:
            ann = span.analysis[0]
        elif isinstance(span, dict):
            ann = span

        form = None
        lemma = None
        if isinstance(ann, dict):
            form = ann.get("form") or ann.get("form_name")
            lemma = ann.get("lemma") or ann.get("root")
            if not lemma and ann.get("root_tokens"):
                lemma = ann.get("root_tokens")[0]
        else:
            form = getattr(ann, "form", None)
            lemma = getattr(ann, "lemma", None)

        case = _case_from_form(form)
        results.append({
            "token": word.text,
            "case": case or "",
            "nominative": lemma or word.text,
            "target_case_value": ""
        })

        if target_case:
            target_form = _CASE_TO_FORM.get(target_case)
            if target_form:
                synthesized_value = _synthesize_last_token_only(lemma or word.text, target_form)
                if synthesized_value:
                    results[-1]["target_case_value"] = synthesized_value

    return results




def _load_synthesizers():
    synthesizers = []
    for module_path in ("estnltk.vabamorf.morf", "estnltk.vabamorf"):
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            continue
        func = getattr(mod, "synthesize", None)
        if callable(func):
            synthesizers.append(func)
    return synthesizers


def synthesize_with_vabamorf(lemma, form):
    """
    Synthesize lemma with a given Vabamorf form (e.g. "sg g", "pl p").
    Returns [] if synthesis isn't available.
    """
    if not lemma or not form:
        return []

    for synth in _load_synthesizers():
        try:
            return synth(lemma, form=form)
        except TypeError:
            try:
                return synth(lemma, form)
            except Exception:
                continue
        except Exception:
            continue

    return []
