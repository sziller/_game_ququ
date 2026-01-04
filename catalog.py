""" Inventory der Chips """

CHIPS = [{"color": "gray",      "name-DE": "Knallerbse",        "inv": {1: 23, 2: 16, 3: 7}},
         {"color": "orange",    "name-DE": "Kürbis",            "inv": {1: 32, 6: 20}},
         {"color": "red",       "name-DE": "Fliegenpilz",       "inv": {1: 18, 2: 13, 4: 15}},
         {"color": "blue",      "name-DE": "Krähenschädel",     "inv": {1: 22, 2: 15, 4: 15}},
         {"color": "yellow",    "name-DE": "Alraunwurzel",      "inv": {1: 19, 2: 11, 4: 15}},
         {"color": "green",     "name-DE": "Kreuzspinne",       "inv": {1: 25, 2: 15, 4: 18}},
         {"color": "purple",    "name-DE": "Geisteratem",       "inv": {1: 23}},
         {"color": "black",     "name-DE": "Totenkopffalter",   "inv": {1: 26}},
         {"color": "greenred",  "name-DE": "Narrenkraut",       "inv": {1: 25}}]

summe = 0
for item in CHIPS:
    sub = sum(item['inv'].values())
    print(f"{item['name-DE']}: {sub}")
    summe += sub
print(summe)

