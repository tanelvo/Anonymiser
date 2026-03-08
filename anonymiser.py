import random

from name_gender import pick_replacement_first
from morphology import analyze_morphology, synthesize_with_vabamorf

family_names = ["Ivanov", "Tamm", "Saar", "Sepp", "Mägi", "Smirnov", "Kukk", "Ilves", "Rebane", "Kuusk"]
locations = ["Kivi", "Lehe", "Pähkli"]
phone_numbers = ["+37255511111", "+37255522222", "+37255533333"]
emails = ["anon1@email.com", "anon2@email.com", "anon3@email.com"]
org_names = ["Firmafy", "Ettevõte OÜ", "AS Firma"]
id_numbers = ["32345678901", "48765432109", "55555555555"]
dates = ["01.01.2000", "12.12.1999", "24.07.2002"]
years = ["1998", "2001", "2005"]
addresses = ["Kivi 1", "Lehe 12", "Pargi 3"]
CASE_TO_VABAMORF = {
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


def infer_case_form(text):
    if analyze_morphology is None:
        return None
    try:
        analyses = analyze_morphology(text)
    except Exception:
        return None
    if not analyses:
        return None
    feats = analyses[0].get("feats", "")
    if "Case=" not in feats:
        return None
    for part in feats.split("|"):
        if part.startswith("Case="):
            case = part.split("=", 1)[1]
            vabamorf_case = CASE_TO_VABAMORF.get(case)
            return vabamorf_case
    return None

def anonymize_text(data):
    text = data["text"]
    matches = data["matches"]
    anonymize = data["anonymize"]

    if anonymize == "asterisk":
        for match in matches:
            for slot in match["slots"]:
                start, end = slot
                # Replace the matched text with asterisks
                text = text[:start] + '*' * (end - start) + text[end:]
        return text

    
    replacements = []
    for match in matches:
        match_text = match["match"]
        custom_replacement = match.get("custom", None)
        match_type = match["type"]

        # Determine the replacement based on type
        if match_type == "person":
            # Split the match text to handle first and last names
            match_parts = match_text.split()
            first_name = match_parts[0] if match_parts else ""
            last_name = match_parts[1] if len(match_parts) > 1 else None
            if custom_replacement:
                replacement_first, replacement_last = custom_replacement.split() if ' ' in custom_replacement else (custom_replacement, "")
            else:
                replacement_first = pick_replacement_first(first_name)
                replacement_last = random.choice(family_names)

            has_capitalized_last_name = False
            if last_name:
                has_capitalized_last_name = (
                    last_name[0].isupper()
                    and len(last_name) > 1
                    and last_name[1:].islower()
                )
            for slot in match["slots"]:
                start, end = slot
                slot_text = text[start:end]
                slot_first = replacement_first
                slot_last = replacement_last
                case_form = infer_case_form(slot_text)
                print("========================================")
                print(f"[vabamorf] source='{slot_text}' case='{case_form}'")
                if case_form and synthesize_with_vabamorf is not None:
                    try:
                        synthesized_first = synthesize_with_vabamorf(replacement_first, case_form)
                        if synthesized_first:
                            slot_first = synthesized_first[0]
                        if replacement_last:
                            synthesized_last = synthesize_with_vabamorf(replacement_last, case_form)
                            if synthesized_last:
                                slot_last = synthesized_last[0]
                        print(f"[vabamorf] nom='{replacement_first} {replacement_last}'. case='{case_form}'. inflected='{slot_first} {slot_last}'")
                    except Exception:
                        pass
                
                # Determine if the slot corresponds to the full name, first name, or last name
                if " " not in slot_text:
                    # Single-token slot (often inflected) -> replace whole token
                    replacements.append((start, end, slot_first))
                elif slot_text == first_name:  # First name only
                    replacements.append((start, end, slot_first))
                elif last_name and has_capitalized_last_name and slot_text == last_name:  # Last name only
                    replacements.append((start, end, slot_last))
                else:  # Full name with space
                    replacements.append((start, start + len(first_name), slot_first))
                    if last_name and has_capitalized_last_name:
                        replacements.append((start + len(first_name) + 1, end, slot_last))
                    
        elif match_type == "location":
            replacement = random.choice(locations)
            for slot in match["slots"]:
                start, end = slot
                replacements.append((start, end, replacement))

        elif match_type == "email_addresses":
            replacement = random.choice(emails)
            for slot in match["slots"]:
                start, end = slot
                replacements.append((start, end, replacement))

        elif match_type == "phone_numbers":
            replacement = random.choice(phone_numbers)
            for slot in match["slots"]:
                start, end = slot
                replacements.append((start, end, replacement))

        elif match_type == "id_numbers":
            replacement = random.choice(id_numbers)
            for slot in match["slots"]:
                start, end = slot
                replacements.append((start, end, replacement))

        elif match_type == "organisation":
            replacement = random.choice(org_names)
            for slot in match["slots"]:
                start, end = slot
                replacements.append((start, end, replacement))
        elif match_type == "dates":
            for slot in match["slots"]:
                start, end = slot
                matched = text[start:end]
                if matched.isdigit() and len(matched) == 4:
                    replacement = random.choice(years)
                elif '-' in matched and matched[:4].isdigit():
                    replacement = "2000-01-01"
                elif '/' in matched:
                    replacement = "01/01/2000"
                else:
                    replacement = random.choice(dates)
                replacements.append((start, end, replacement))
        elif match_type == "addresses":
            replacement = random.choice(addresses)
            for slot in match["slots"]:
                start, end = slot
                replacements.append((start, end, replacement))

    # Sort replacements by the start index in descending order to avoid index shifts during replacement
    replacements = sorted(replacements, key=lambda x: x[0], reverse=True)

    # Replace all occurrences in the text
    for start, end, replacement in replacements:
        text = text[:start] + replacement + text[end:]

    print(f"[anonymized] {text}")
    return text
