"""Survival quiz scenarios: built-in seeds first, then Gemini drafts. All need human review.."""
import json
import os
import re

import requests

BANNED = re.compile(
    r"\b(edible|forag\w*|mushroom\w*|berr(?:y|ies)|medicin\w*|dose|dosage|antibiotic\w*|"
    r"tourniquet|suture|gun|firearm|rifle|trap(?:s|ping)?|poison\w*|purif\w*|bleach)\b",
    re.I,
)

SEEDS = [
 {"id":"lost-forest","hook":"Lost in the forest. Night is coming.","question":"What do you do first?",
  "options":["Keep walking fast","Stop and stay put","Climb the nearest hill"],"correct":1,
  "explanation":"Stop, stay calm and make a plan. Moving while lost usually makes you harder to find.",
  "search_terms":["dense forest","forest dusk","foggy woods"],"summary_it":"Perso nel bosco: fermati e resta dove sei."},
 {"id":"rip-current","hook":"A rip current drags you out to sea.","question":"How do you escape?",
  "options":["Swim straight to shore","Dive under the water","Float, then swim parallel"],"correct":2,
  "explanation":"Don't fight the current. Stay afloat and swim parallel to the shore to leave it.",
  "search_terms":["ocean waves","rough sea","beach waves"],"summary_it":"Corrente di risacca: galleggia e nuota parallelo alla riva."},
 {"id":"flooded-river","hook":"The trail is cut by a fast, rising river.","question":"What is the safest move?",
  "options":["Turn back or wait","Wade across quickly","Cross with a rope"],"correct":0,
  "explanation":"Fast water can knock you down at shallow depths. Turning back beats any crossing.",
  "search_terms":["fast river","mountain river","rapids"],"summary_it":"Fiume in piena: torna indietro o aspetta."},
 {"id":"lightning-ridge","hook":"A storm hits while you're on an exposed ridge.","question":"Where do you go?",
  "options":["Under the tallest tree","Down off the ridge, fast","Stay on the summit"],"correct":1,
  "explanation":"High ground and lone trees are the danger. Descend immediately and seek a safer shelter.",
  "search_terms":["mountain storm","storm clouds mountains","mountain ridge"],"summary_it":"Temporale in cresta: scendi subito, evita alberi isolati."},
 {"id":"moose-charge","hook":"A moose charges straight at you.","question":"What do you do?",
  "options":["Play dead","Stand your ground","Run behind a tree"],"correct":2,
  "explanation":"Unlike most bear encounters, you should run from a moose. Put something solid between you.",
  "search_terms":["boreal forest","pine forest","northern wilderness"],"summary_it":"Alce alla carica: corri e mettiti dietro un albero."},
 {"id":"cougar","hook":"A mountain lion is staring at you.","question":"What is your move?",
  "options":["Look big and back away","Turn and sprint","Crouch and hide"],"correct":0,
  "explanation":"Never run. Face it, look large, make noise and back away. If attacked, fight back.",
  "search_terms":["rocky canyon","mountain wilderness","desert canyon"],"summary_it":"Puma: non correre, sembra grande, indietreggia; se attacca reagisci."},
 {"id":"black-bear","hook":"A black bear stands on the trail ahead.","question":"What do you do?",
  "options":["Run downhill","Back away slowly, talking","Climb a tree"],"correct":1,
  "explanation":"Don't run or climb. Stay calm, speak firmly and back away while facing the bear.",
  "search_terms":["forest trail","woodland path","mountain trail"],"summary_it":"Orso nero: non correre, indietreggia parlando con calma."},
 {"id":"snakebite","hook":"A venomous snake bites your leg.","question":"What comes first?",
  "options":["Suck out the venom","Tie it off tightly","Stay still and call for help"],"correct":2,
  "explanation":"Keep calm and still, remove tight items and get emergency care. Don't cut or suck the bite.",
  "search_terms":["desert landscape","dry grassland","rocky desert"],"summary_it":"Morso di serpente: resta fermo e chiama i soccorsi."},
 {"id":"wet-cold","hook":"You're soaked, shivering and the wind is rising.","question":"What matters most?",
  "options":["Get out of the wind and wet","Keep walking in wet clothes","Drink something strong"],"correct":0,
  "explanation":"Wet clothes and wind steal heat fast. Get sheltered, change into dry layers and insulate.",
  "search_terms":["cold rain forest","windy mountains","winter wilderness"],"summary_it":"Bagnato e al freddo: riparati e metti strati asciutti."},
 {"id":"thin-ice","hook":"The ice breaks and you fall into a frozen lake.","question":"How do you get out?",
  "options":["Stand and climb out","Kick flat, then roll away","Wait without moving"],"correct":1,
  "explanation":"Get horizontal, kick and pull yourself onto the ice, then roll away to spread your weight.",
  "search_terms":["frozen lake","winter lake","ice lake"],"summary_it":"Ghiaccio rotto: scalcia in orizzontale e rotola via."},
 {"id":"snow-water","hook":"You're thirsty and surrounded by snow.","question":"What do you do?",
  "options":["Eat handfuls of snow","Ignore the thirst","Melt it first"],"correct":2,
  "explanation":"Eating snow chills your body. Melt it first, and treat the water when you can.",
  "search_terms":["snowy mountains","snow forest","winter landscape"],"summary_it":"Sete sulla neve: sciogli la neve, non mangiarla."},
 {"id":"quicksand","hook":"You sink into quicksand up to your knees.","question":"How do you escape?",
  "options":["Pull one leg out hard","Lean back and move slowly","Struggle as fast as you can"],"correct":1,
  "explanation":"Panic digs you deeper. Lean back to spread your weight and work your legs free slowly.",
  "search_terms":["muddy river","wetland","tidal flats"],"summary_it":"Sabbie mobili: appoggiati all'indietro e muoviti piano."},
]

SCHEMA = {"type":"OBJECT","required":["id","hook","question","options","correct","explanation","search_terms","summary_it"],
  "properties":{"id":{"type":"STRING"},"hook":{"type":"STRING"},"question":{"type":"STRING"},
  "options":{"type":"ARRAY","items":{"type":"STRING"}},"correct":{"type":"INTEGER"},
  "explanation":{"type":"STRING"},"search_terms":{"type":"ARRAY","items":{"type":"STRING"}},
  "summary_it":{"type":"STRING"}}}


def validate(s):
    if len(s.get("options", [])) != 3 or s.get("correct") not in (0, 1, 2):
        raise ValueError("needs 3 options and a valid answer index")
    limits = (("hook", 60), ("question", 40), ("explanation", 110))
    for key, limit in limits:
        if not s.get(key) or len(s[key]) > limit:
            raise ValueError(f"{key} missing or longer than {limit} chars")
    if any(len(o) > 30 for o in s["options"]):
        raise ValueError("option too long")
    if not s.get("search_terms"):
        raise ValueError("search_terms missing")
    if BANNED.search(json.dumps(s)):
        raise ValueError("banned topic")
    s["id"] = re.sub(r"[^a-z0-9-]", "-", s["id"].lower()).strip("-")[:40]
    if not s["id"]:
        raise ValueError("id missing")
    return s


def from_gemini(used):
    prompt = ("Write one wilderness safety quiz for a 15-second vertical video, in English. "
      "Use only widely accepted guidance from parks, coast guards or rescue organisations. "
      "Exclude foraging, wild food, medicine, weapons, traps and water purification. "
      "Hook max 60 chars, question max 40, explanation max 110, each of 3 options max 30. "
      "correct is the 0-based answer index; vary it. Do not exaggerate. "
      "search_terms: 3 landscape-only stock footage queries, no people or animals. "
      "summary_it: one Italian sentence with the answer. "
      f"Do not reuse these ids: {sorted(used)}")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json={"contents":[{"parts":[{"text":prompt}]}],
              "generationConfig":{"responseMimeType":"application/json","responseSchema":SCHEMA}},
        timeout=60)
    r.raise_for_status()
    s = validate(json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"]))
    if s["id"] in used:
        raise ValueError("id already used")
    s["ai_draft"] = True
    return s


def next_scenario(used):
    for s in SEEDS:
        if s["id"] not in used:
            return dict(s)
    return from_gemini(used)


def caption(s, credit):
    text = (f"{s['hook']} {s['question']} Comment A, B or C before the reveal.\n\n"
            "General safety information. Follow local authorities and rangers.\n"
            f"{credit}\n\n#survival #wilderness #outdoors #nature #hiking")
    return text[:2200]
