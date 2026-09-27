"""Test 3: the typed questions, in English and in Finnish, and the three conditions.

Every engine gets the same Jev question dict. What changes per condition is the language of the text and the
language of the question (instructions, option names and descriptions):

  en     English text,  English question     parallel sets only: the English score on the same items
  fi-en  Finnish text,  English question     keep one English question dict for every language
  fi     Finnish text,  Finnish question     everything in Finnish

Option names differ per language ("sports" / "urheilu"); answers are mapped back to the canonical gold ids.
"""

CONDITIONS = {"en": ("en", "en"), "fi-en": ("fi", "en"), "fi": ("fi", "fi")}      # condition -> (text, question)

# canonical id -> {language: (option name, description)}
SIB = {
    "instructions": {"en": "What is the topic of this text?", "fi": "Mikä on tämän tekstin aihe?"},
    "options": {
        "science/technology": {"en": ("science/technology", "science, research, technology or engineering"),
                               "fi": ("tiede/teknologia", "tiede, tutkimus, teknologia tai tekniikka")},
        "travel": {"en": ("travel", "travelling, tourism, sights and getting around as a traveller"),
                   "fi": ("matkailu", "matkustaminen, turismi, nähtävyydet ja liikkuminen matkailijana")},
        "politics": {"en": ("politics", "government, elections, laws and international relations"),
                     "fi": ("politiikka", "hallinto, vaalit, lait ja kansainväliset suhteet")},
        "sports": {"en": ("sports", "sports, athletes, matches and competitions"),
                   "fi": ("urheilu", "urheilu, urheilijat, ottelut ja kilpailut")},
        "health": {"en": ("health", "health, medicine, illness and the body"),
                   "fi": ("terveys", "terveys, lääketiede, sairaudet ja keho")},
        "entertainment": {"en": ("entertainment", "films, music, television, celebrities, games and the arts"),
                          "fi": ("viihde", "elokuvat, musiikki, televisio, julkkikset, pelit ja taide")},
        "geography": {"en": ("geography", "countries, landscapes, climate, nature and places on Earth"),
                      "fi": ("maantiede", "maat, maisemat, ilmasto, luonto ja paikat maapallolla")},
    },
}

MASSIVE = {
    "instructions": {"en": "What does the user want the assistant to do?",
                     "fi": "Mitä käyttäjä haluaa avustajan tekevän?"},
    "options": {
        "alarm_set": {"en": ("set alarm", "set or schedule an alarm"),
                      "fi": ("aseta herätys", "aseta tai ajasta herätys")},
        "weather_query": {"en": ("weather", "ask about the weather or the forecast"),
                          "fi": ("sää", "kysy säätä tai sääennustetta")},
        "play_music": {"en": ("play music", "play a song, an artist, an album or some music"),
                       "fi": ("soita musiikkia", "soita kappale, artisti, albumi tai musiikkia")},
        "calendar_set": {"en": ("add to calendar", "create a calendar event, meeting or reminder"),
                         "fi": ("lisää kalenteriin", "luo kalenteritapahtuma, tapaaminen tai muistutus")},
        "email_sendemail": {"en": ("send email", "write or send an email"),
                            "fi": ("lähetä sähköposti", "kirjoita tai lähetä sähköposti")},
        "datetime_query": {"en": ("date or time", "ask what time or date it is, here or somewhere else"),
                           "fi": ("päivä tai aika", "kysy kellonaikaa tai päivämäärää, täällä tai muualla")},
        "iot_hue_lightoff": {"en": ("lights off", "turn the lights off"),
                             "fi": ("valot pois", "sammuta valot")},
        "news_query": {"en": ("news", "ask for the news or headlines"),
                       "fi": ("uutiset", "kysy uutisia tai otsikoita")},
        "transport_ticket": {"en": ("book ticket", "book a train, bus or plane ticket"),
                             "fi": ("varaa lippu", "varaa juna-, bussi- tai lentolippu")},
        "cooking_recipe": {"en": ("recipe", "ask for a recipe or how to cook something"),
                           "fi": ("resepti", "kysy reseptiä tai ohjetta jonkin ruoan valmistamiseen")},
    },
}
MASSIVE_INTENTS = list(MASSIVE["options"])

SCANDISENT = {
    "instructions": {"en": "What is the overall sentiment of this review?",
                     "fi": "Mikä on tämän arvostelun yleinen sävy?"},
    "options": {
        "negative": {"en": ("negative", "unhappy, disappointed or critical"),
                     "fi": ("negatiivinen", "tyytymätön, pettynyt tai kriittinen")},
        "positive": {"en": ("positive", "happy, satisfied or praising"),
                     "fi": ("positiivinen", "tyytyväinen, iloinen tai kehuva")},
    },
}

# Belebele: the question and the four answers are part of each item (already in the text's language); only the
# framing around the question follows the question language. Options are A-D with the answer as description.
BELEBELE_FRAME = {"en": "Answer this question about the text: ", "fi": "Vastaa tähän tekstiä koskevaan kysymykseen: "}

TASKS = {"sib": SIB, "massive": MASSIVE, "scandisent": SCANDISENT}


def conditions_for(item):
    return [c for c, (text_lang, _) in CONDITIONS.items() if item[text_lang] is not None]


def request(dataset, item, condition):
    """-> (Jev request {"state", "questions"}, {option name: canonical id})"""
    text_lang, q_lang = CONDITIONS[condition]
    side = item[text_lang]
    if dataset == "belebele":
        crit = dict(zip("ABCD", side["answers"]))
        q = {"type": "choice", "instructions": BELEBELE_FRAME[q_lang] + side["question"], "criteria": crit}
        return {"state": side["text"], "questions": {"q": q}}, {k: k for k in crit}
    task = TASKS[dataset]
    crit, back = {}, {}
    for canon, langs in task["options"].items():
        name, desc = langs[q_lang]
        crit[name], back[name] = desc, canon
    q = {"type": "choice", "instructions": task["instructions"][q_lang], "criteria": crit}
    return {"state": side["text"], "questions": {"q": q}}, back
