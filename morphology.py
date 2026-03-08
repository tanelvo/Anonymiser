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
        print(text_obj.tag_layer(["morph_analysis"]))
        if "morph_analysis" in text_obj.layers:
            print(text_obj["morph_analysis"])
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

    return " ".join(tokens)




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
