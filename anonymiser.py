import random

# Define a list of gender-neutral names to use for replacements
gender_neutral_names = ["Kris", "Renee", "Keit", "Toni", "Kai", "Eike", "Maiki", "Julian", "Karla", "Erli"]
family_names = ["Ivanov", "Tamm", "Saar", "Sepp", "Mägi", "Smirnov", "Kukk", "Ilves", "Rebane", "Kuusk"]
locations = ["Kivi", "Lehe", "Pähkli"]
phone_numbers = ["+37255511111", "+37255522222", "+37255533333"]
emails = ["anon1@email.com", "anon2@email.com", "anon3@email.com"]
org_names = ["Firmafy", "Ettevõte OÜ", "AS Firma"]
id_numbers = ["32345678901", "48765432109", "55555555555"]

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
            if custom_replacement:
                replacement_first, replacement_last = custom_replacement.split() if ' ' in custom_replacement else (custom_replacement, "")
            else:
                replacement_first = random.choice(gender_neutral_names)
                replacement_last = random.choice(family_names)

            # Split the match text to handle first and last names
            match_parts = match_text.split()
            first_name = match_parts[0]
            last_name = match_parts[1] if len(match_parts) > 1 else None
            
            for slot in match["slots"]:
                start, end = slot
                
                # Determine if the slot corresponds to the full name, first name, or last name
                if text[start:end] == first_name:  # First name only
                    replacements.append((start, end, replacement_first))
                elif last_name and text[start:end] == last_name:  # Last name only
                    replacements.append((start, end, replacement_last))
                else:  # Full name
                    replacements.append((start, start + len(first_name), replacement_first))
                    replacements.append((start + len(first_name) + 1, end, replacement_last))
                    
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

    # Sort replacements by the start index in descending order to avoid index shifts during replacement
    replacements = sorted(replacements, key=lambda x: x[0], reverse=True)

    # Replace all occurrences in the text
    for start, end, replacement in replacements:
        text = text[:start] + replacement + text[end:]

    return text
