import ephem
from math import degrees

# 27 Nakshatras
nakshatras = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Moola", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

# Brief Nakshatra details
nakshatra_details = {
    "Ashwini": "Ashwini Nakshatra, the first lunar mansion, is symbolized by the horse-headed twins and ruled by Ketu. Known for vitality, quick action, and healing powers, it represents beginnings and fertility. Agriculturally, it is ideal for sowing fast-growing crops like leafy greens, spinach, and fenugreek, as its energy supports quick sprouting and early harvests.",

    "Bharani": "Bharani Nakshatra, ruled by Venus and symbolized by the womb, signifies discipline, endurance, and transformation. It carries fiery energy and is associated with survival and resilience. In farming, it favors hardy pulses, pigeon pea, and drought-tolerant crops, reflecting its ability to sustain growth under stress.",

    "Krittika": "Krittika Nakshatra, ruled by the Sun and symbolized by a sharp blade, embodies fire, purification, and transformative energy. It is linked with strength and intensity. Agriculturally, it is ideal for heat-loving crops like chilies, onions, and mustard, as well as spices that thrive under strong sunlight.",

    "Rohini": "Rohini Nakshatra, ruled by the Moon and symbolized by a chariot, is considered the most fertile of all nakshatras. It represents abundance, growth, and nourishment. Farmers favor Rohini for sowing rice, wheat, and sugarcane, as it ensures strong germination and high yields, symbolizing prosperity and stability.",

    "Mrigashira": "Mrigashira Nakshatra, ruled by Mars and symbolized by a deer’s head, embodies curiosity, adaptability, and exploration. Agriculturally, it supports diverse planting, especially legumes, beans, and vegetables, as its airy quality encourages branching and quick harvest cycles.",

    "Ardra": "Ardra Nakshatra, ruled by Rahu and symbolized by a teardrop, represents transformation, storms, and renewal. Its moist and restless nature makes it favorable for medicinal herbs and plants requiring significant water, such as ginger and mint. It is believed to foster crops with healing properties.",

    "Punarvasu": "Punarvasu Nakshatra, ruled by Jupiter and symbolized by a quiver of arrows, signifies renewal, nourishment, and optimism. In agriculture, it is associated with pulses, beans, and millets, as its energy restores fertility and promotes sustainable farming cycles.",

    "Pushya": "Pushya Nakshatra, ruled by Saturn and symbolized by the cow’s udder, embodies nourishment, protection, and auspiciousness. It is one of the most favorable nakshatras for farming. Traditionally, it is linked to pulses, oilseeds, and long-term crops, as its nurturing influence ensures soil fertility and abundant harvests.",

    "Ashlesha": "Ashlesha Nakshatra, ruled by Mercury and symbolized by a coiled serpent, represents intensity, binding, and transformation. In agriculture, it is connected with creepers, climbers, and root crops like ginger and garlic, reflecting its penetrating and entwining energy.",

    "Magha": "Magha Nakshatra, ruled by Ketu and symbolized by a throne, signifies ancestry, tradition, and authority. It is associated with strength and endurance. Agriculturally, it is suited for hardy perennial shrubs and long-standing crops that can withstand harsh conditions, such as castor and arhar.",

    "Purva Phalguni": "Purva Phalguni Nakshatra, ruled by Venus and symbolized by a bed, represents creativity, joy, and fertility. It supports ornamental crops, fruits, and flowers such as bananas, papayas, and marigolds, symbolizing beauty and abundance in farming.",

    "Uttara Phalguni": "Uttara Phalguni Nakshatra, ruled by the Sun and symbolized by the bed’s back leg, represents contracts, growth, and sustainability. It is linked with grains, sugarcane, and orchard crops, as its stable influence ensures steady and reliable yields.",

    "Hasta": "Hasta Nakshatra, ruled by the Moon and symbolized by a hand, embodies dexterity, growth, and productivity. Agriculturally, it supports crops like cucumbers, bananas, and coconuts, reflecting nourishment and abundance under its influence.",

    "Chitra": "Chitra Nakshatra, ruled by Mars and symbolized by a bright jewel, represents creativity, construction, and beauty. In farming, it is linked with medicinal herbs, ornamental plants, and horticultural crops, symbolizing vitality and refinement.",

    "Swati": "Swati Nakshatra, ruled by Rahu and symbolized by a young sprout swaying in the wind, signifies independence, flexibility, and adaptability. Agriculturally, it favors airy, wind-tolerant crops like maize, sorghum, and millets, reflecting its light and mobile qualities.",

    "Vishakha": "Vishakha Nakshatra, ruled by Jupiter and symbolized by a triumphal arch, represents branching, determination, and duality. In farming, it is associated with pulses, sesame, and branching crops, symbolizing persistence and productivity.",

    "Anuradha": "Anuradha Nakshatra, ruled by Saturn and symbolized by the lotus, represents devotion, discipline, and cooperation. Agriculturally, it is linked with rice, grains, and turmeric, reflecting its moist, fertile, and steady qualities that promote nourishment.",

    "Jyeshtha": "Jyeshtha Nakshatra, ruled by Mercury and symbolized by an earring, signifies seniority, responsibility, and intensity. In farming, it is connected with ginger, leafy greens, and herbs that require close care, reflecting its protective but demanding energy.",

    "Moola": "Moola Nakshatra, ruled by Ketu and symbolized by roots tied together, represents foundations, depth, and transformation. Agriculturally, it favors root crops such as potatoes, turmeric, carrots, and beetroots, symbolizing growth from the ground up.",

    "Purva Ashadha": "Purva Ashadha Nakshatra, ruled by Venus and symbolized by a fan, signifies fertility, invigoration, and strength. It is agriculturally connected with watery, high-yield crops like rice and sugarcane, reflecting its nourishing influence.",

    "Uttara Ashadha": "Uttara Ashadha Nakshatra, ruled by the Sun and symbolized by an elephant’s tusk, represents firmness, leadership, and reliability. In agriculture, it supports wheat, orchard fruits, and grains, reflecting its steady and enduring qualities.",

    "Shravana": "Shravana Nakshatra, ruled by the Moon and symbolized by an ear, signifies learning, listening, and preservation. Agriculturally, it is associated with cereals, fodder crops, and grains, reflecting its stable and sustaining qualities.",

    "Dhanishta": "Dhanishta Nakshatra, ruled by Mars and symbolized by a drum, represents rhythm, prosperity, and resourcefulness. In farming, it is suited for fodder crops, millets, and maize, symbolizing abundance and communal nourishment.",

    "Shatabhisha": "Shatabhisha Nakshatra, ruled by Rahu and symbolized by a circle, signifies healing, mystery, and protection. Agriculturally, it is associated with medicinal crops, tubers, and unique herbs, reflecting its restorative nature.",

    "Purva Bhadrapada": "Purva Bhadrapada Nakshatra, ruled by Jupiter and symbolized by a sword, represents transformation, austerity, and intensity. In farming, it is connected with hardy oilseeds and crops that withstand harsher climates, reflecting its fiery energy.",

    "Uttara Bhadrapada": "Uttara Bhadrapada Nakshatra, ruled by Saturn and symbolized by the back legs of a funeral cot, represents stability, depth, and nourishment. Agriculturally, it supports crops like rice, sugarcane, and long-duration grains, reflecting endurance and prosperity.",

    "Revati": "Revati Nakshatra, ruled by Mercury and symbolized by a fish, represents nourishment, prosperity, and completion. It is agriculturally associated with rice, pulses, and leafy greens, as its gentle influence ensures sweetness, quality, and abundance in the harvest."
}

# Nakshatra Ratings + Expanded Crop Sets
nakshatra_crops = {
    0: {"Rating": 3, "Crops": ["Leafy greens", "Spinach", "Fenugreek", "Short-duration vegetables"]},
    1: {"Rating": 2, "Crops": ["Horse gram", "Pigeon pea", "Cowpea"]},
    2: {"Rating": 3, "Crops": ["Mustard", "Chili", "Onion", "Spices"]},
    3: {"Rating": 5, "Crops": ["Rice", "Wheat", "Sugarcane", "Barley"]},
    4: {"Rating": 4, "Crops": ["Beans", "Cucumber", "Okra", "Legumes"]},
    5: {"Rating": 3, "Crops": ["Medicinal herbs", "Tulsi", "Mint"]},
    6: {"Rating": 4, "Crops": ["Millets", "Bajra", "Foxtail millet"]},
    7: {"Rating": 5, "Crops": ["Black gram", "Soybean", "Sesame"]},
    8: {"Rating": 3, "Crops": ["Ginger", "Garlic", "Bottle gourd", "Creepers"]},
    9: {"Rating": 2, "Crops": ["Perennial shrubs", "Castor", "Arhar"]},
    10: {"Rating": 4, "Crops": ["Cotton", "Marigold", "Banana", "Papaya"]},
    11: {"Rating": 5, "Crops": ["Sugarcane", "Rice", "Fruit orchards"]},
    12: {"Rating": 4, "Crops": ["Banana", "Coconut", "Cucumber", "Melon"]},
    13: {"Rating": 3, "Crops": ["Aloe vera", "Tulsi", "Medicinal flowers"]},
    14: {"Rating": 4, "Crops": ["Maize", "Jowar", "Ragi"]},
    15: {"Rating": 3, "Crops": ["Sesame", "Pulses", "Groundnut"]},
    16: {"Rating": 4, "Crops": ["Turmeric", "Rice", "Finger millet"]},
    17: {"Rating": 2, "Crops": ["Ginger", "Spinach", "Leafy vegetables"]},
    18: {"Rating": 3, "Crops": ["Potato", "Turmeric", "Carrot", "Beetroot"]},
    19: {"Rating": 4, "Crops": ["Rice", "Sugarcane", "Turmeric"]},
    20: {"Rating": 5, "Crops": ["Wheat", "Apples", "Pears", "Orchards"]},
    21: {"Rating": 5, "Crops": ["Fodder crops", "Rice", "Cereals"]},
    22: {"Rating": 4, "Crops": ["Maize", "Jowar", "Fodder grasses"]},
    23: {"Rating": 3, "Crops": ["Medicinal roots", "Sweet potato", "Yam"]},
    24: {"Rating": 2, "Crops": ["Linseed", "Castor", "Sesame"]},
    25: {"Rating": 5, "Crops": ["Sugarcane", "Paddy", "Vegetables"]},
    26: {"Rating": 5, "Crops": ["Rice", "Green gram", "Spinach", "Amaranth"]}
}

def get_moon_nakshatra_and_crop(date_str):
    """
    Input: date_str = 'YYYY-MM-DD'
    Output: Moon longitude, Nakshatra, Rating, Recommended Crops, Nakshatra Details
    """
    date = date_str + " 12:00"  # UTC noon
    moon = ephem.Moon(date)

    # Approximate Moon longitude
    moon_longitude = degrees(moon.ra)

    # Nakshatra index
    nak_index = int(moon_longitude // (360 / 27)) % 27
    nak_name = nakshatras[nak_index]

    # Crop recommendation
    crop_info = nakshatra_crops[nak_index]

    return {
        "Moon_Longitude": round(moon_longitude, 2),
        "Nakshatra_Index": nak_index,
        "Nakshatra_Name": nak_name,
        "Nakshatra_Details": nakshatra_details.get(nak_name, "No details available"),
        "Rating": crop_info["Rating"],
        "Recommended_Crops": crop_info["Crops"]
    }