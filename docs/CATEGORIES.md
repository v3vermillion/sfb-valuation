# Categories: how every item is labelled

Every kept item carries one category: **what the item is**, the way a grocery or general-merchandise store would label
it on the shelf. Walmart's own category path is a hint, never the answer: its feed files turtlenecks under Meat & Seafood,
cookbooks under Baking and coffee filters under Coffee. `crawler/classify.py` applies these rules; `data/categories.json`
holds the ids and names. The rules are measured against a hand-labelled sample (`tests/fixtures/category-gold.jsonl`),
and every snapshot's 300-row sample review checks the category as well.

## Not carried at all (excluded everywhere, whatever the department)

| Reason | What |
|---|---|
| `apparel` | Clothing of any kind, for adults, children, babies or pets: tops, bottoms, dresses, outerwear, sleepwear, underwear and bras, socks and hosiery (compression socks included), swimwear, uniforms, costumes, hats, caps, gloves, mittens, scarves, belts, ties. Not apparel: disposable incontinence underwear and diapers (Personal Care / Baby), bibs (Baby), orthopedic braces and supports (Health). |
| `footwear` | Shoes, boots, sneakers, sandals, slippers, cleats, flip-flops, baby shoes. Not footwear: insoles, foot care, shoe polish and laces. |
| `pet_bed` | Pet beds and bed-like pet cushions, mats and crate pads. |
| `alcohol` | Beer, wine, spirits, hard cider and hard seltzer. Non-alcoholic mixers and cooking wine stay in their aisle. |
| `tobacco` | Cigarettes, cigars, tobacco, vapes and e-liquid. Stop-smoking aids (nicotine gum, patches, lozenges) are Health & Medicine. |
| `media` | Books, music, movies and video games found outside the Books department (cookbooks under Food, CDs under Beverages). |
| `large_equipment` | Massage chairs and recliners, mobility scooters, power wheelchairs, patient lifts, hospital beds, treadmills, ellipticals, exercise bikes and home gyms (multi-gyms, power racks and cages, power towers, functional trainers, Smith machines), priced $100 or more. Not excluded: walkers, rollators, canes, shower chairs, manual wheelchairs, dumbbells, bands, and parts or accessories (slings, sheets, ramps, baskets, cushions). |

## Listings that are not products

Not carried: test listings (`Signing Test 9027 Dummy Stress Test`, `TEST ITEM 3`, or any placeholder name on an internal
4-prefix barcode) → `test_listing`; store displays and pallets (`0523 Infinity PDQ`, `64PC OS SOS 1/2 Plt`, `FF Half Mod`,
`Axe Kenobi Split EC`, `C&B SS Shipper`, `DISP SLIDE2ME 2024`, `Section Header Kit`) → `store_display`.

Kept for barcode lookup only (`placeholder` flag): every other name that identifies no product: `Merchandise`, a brand
alone (`PROGRESSO`), `Discontinued by Supplier`, `coming soon`, a supplier code, `DO NOT USE- ...`, an old seasonal listing
(`***holiday 2014***...`). Only with a valid check digit and a price that passes the price sanity rule; otherwise dropped
(`placeholder_no_barcode`, `placeholder_price`). Never in typed search; not in the size-parse rate. The name is replaced by
another Walmart listing's name for the same UPC, else the Open Facts name for the UPC (flag `name_filled`, source in
`name_src`); with neither, the name is `(name not provided)`, shown after the brand. A real product name carrying a
`***Discontinued***` marker is not a placeholder: the marker is removed and the item is flagged `discontinued`.

## Food

| id | Category | Includes | Boundaries |
|---|---|---|---|
| 1 | Produce | Fresh fruit and vegetables, fresh herbs, bagged salads and salad kits, fresh-cut fruit and vegetable trays, fresh mushrooms | Dried fruit → Snacks; canned or jarred produce → Canned; frozen → Frozen |
| 2 | Dairy & Eggs | Milk (dairy, plant-based, shelf-stable), cream, liquid creamer, butter and margarine, cheese, yogurt, sour cream, cottage cheese, eggs and egg substitutes, refrigerated dough, whipped topping | Powdered creamer → Beverages; sliced deli cheese → Deli |
| 3 | Meat & Seafood | Fresh and refrigerated meat, poultry, fish and shellfish, bacon, sausage, hot dogs, ham | Canned meat or fish → Canned; frozen → Frozen; jerky and meat sticks → Snacks; sliced lunch meat → Deli |
| 4 | Deli & Prepared Foods | Sliced deli meat and cheese, lunch meat, rotisserie and prepared meals and sides, refrigerated salads, hummus and refrigerated dips, lunch kits, sandwiches, charcuterie and snack trays | Shelf-stable dips and salsa → Condiments |
| 5 | Frozen Foods | Everything sold frozen: meals, pizza, vegetables, fruit, meat and seafood, breakfast, desserts, ice cream, frozen bread | |
| 6 | Canned & Jarred Foods | Canned or jarred vegetables, fruit, beans, meat and fish (tuna, chicken, Spam, Vienna sausage), soup, broth, chili, stew, canned pasta, applesauce and fruit cups, shelf-stable meals in a can or cup | Pasta sauce, pickles, olives → Condiments; peanut butter → Spreads (Condiments) |
| 7 | Pasta, Rice & Dry Goods | Pasta and noodles, ramen and instant noodles, rice, grains, dried beans and lentils, boxed meals and side dishes (mac and cheese, rice and pasta mixes, helper kits), instant potatoes, stuffing, taco shells and dinner kits, bread crumbs, soup mixes | |
| 8 | Bread & Bakery | Bread, buns, rolls, tortillas, bagels, English muffins, pita and wraps, bakery cakes, pies, donuts, muffins, pastries, packaged snack cakes, bakery cookies | Packaged cookies → Snacks; frozen bread → Frozen |
| 9 | Snacks & Candy | Chips, pretzels, popcorn, crackers, cookies, nuts and seeds, trail mix, dried fruit, fruit snacks, jerky and meat sticks, protein and snack bars, ready-to-eat pudding and gelatin cups, candy, chocolate, gum, mints, food gift baskets of sweets | Granola and cereal bars → Breakfast |
| 10 | Beverages | Water, soda, juice, sports and energy drinks, coffee (ground, whole bean, pods, instant, bottled), tea, cocoa, powdered drink mixes, drink enhancers, ready-to-drink nutrition and protein shakes, non-alcoholic mixers, powdered creamer, coffee syrups | Protein powder → Health; liquid creamer → Dairy |
| 11 | Condiments, Sauces & Spreads | Ketchup, mustard, mayonnaise, salad dressing, barbecue, hot and soy sauce, pasta and pizza sauce, salsa and shelf-stable dips, gravy, marinades, pickles, relish, olives, peppers in jars, peanut and nut butters, jam and jelly, honey, sweet spreads | Syrup → Breakfast; spices → Baking, Spices & Oils |
| 28 | Baking, Spices & Oils | Flour, sugar and sweeteners, baking mixes, baking chips and chocolate, frosting, sprinkles and edible decorations, food colouring, extracts, yeast, baking powder and soda, cornstarch, gelatin and pudding mix, pie filling, evaporated and condensed milk, cooking oil, shortening, vinegar, cooking spray, salt, pepper, herbs, spices and seasoning mixes | Cupcake liners and pans → Kitchen |
| 29 | Breakfast & Cereal | Cold cereal, granola, oatmeal and hot cereal, grits, pancake and waffle mix, syrup, toaster pastries, granola, cereal and breakfast bars | Frozen waffles → Frozen |

Food gift baskets and assortments are labelled by what they mostly hold (sweets → Snacks & Candy, meat and cheese →
Deli & Prepared, fruit → Produce, coffee or tea → Beverages).

## Everything else

| id | Category | Includes | Boundaries |
|---|---|---|---|
| 13 | Baby | Diapers, baby wipes, formula, baby food and snacks, bottles and feeding, pacifiers, baby bath, skin and health care, nursery, strollers, car seats, baby gear and baby toys | Baby clothing and shoes → excluded |
| 14 | Health & Medicine | Pain relief, cold and allergy, digestive health, vitamins and supplements, protein powder, first aid, medical devices and supplies, diabetes care, eye and ear care, foot care and insoles, sleep aids, stop-smoking aids, braces and supports, reading glasses | |
| 15 | Personal Care | Soap and body wash, body lotion, deodorant, oral care, shaving and hair removal, feminine care, adult incontinence, sexual wellness, cotton balls and swabs, men's grooming | |
| 30 | Beauty | Makeup, nail care, fragrance, facial skincare, sun care, hair care (shampoo, conditioner, styling, colour), hair tools and appliances, hair accessories, beauty tools | |
| 16 | Household Supplies | Cleaning products, laundry, dish soap and dishwasher detergent, paper towels, toilet paper, tissues, napkins, disposable plates, cups and cutlery, foil, plastic wrap, food storage and freezer bags, coffee filters, trash bags, air fresheners, pest control, batteries, light bulbs | |
| 17 | Kitchen & Dining | Cookware, bakeware, cupcake liners, kitchen utensils and gadgets, small kitchen appliances, dinnerware, glassware, drinkware, reusable food storage containers, serving boards and trays, water filters and pitchers | |
| 18 | Home | Bedding, bath towels and rugs, decor, furniture, storage and organisation, lighting, curtains | |
| 31 | Hardware & Tools | Tools, hardware, paint, electrical, plumbing, building supplies | |
| 32 | Lawn, Garden & Floral | Lawn and garden supplies, outdoor furniture, grills, live plants, fresh-cut flowers and bouquets | |
| 19 | Pet Food & Supplies | Pet food and treats, litter, pet health, grooming, toys, bowls, leashes, cages and carriers | Pet beds and pet clothing → excluded |
| 20 | School, Office & Crafts | School and office supplies, paper, writing, backpacks, arts, crafts and sewing | |
| 21 | Toys, Books & Games | Toys, games, puzzles, and books in the Books department | |
| 22 | Seasonal & Party | Party supplies, decorations, gift wrap, greeting cards, birthday candles, cake toppers, seasonal decor | Seasonal food → its food aisle |
| 24 | Auto | Car care, parts, accessories, motor oil | |
| 25 | Electronics | Electronics, phones and accessories, computers, TVs, audio, cables, chargers | Hair appliances → Beauty; kitchen appliances → Kitchen |
| 26 | Jewelry & Accessories | Jewelry, watches, sunglasses, handbags, wallets | |
| 27 | Sports & Outdoors | Exercise and sports equipment, camping, fishing, hunting, bikes | Athletic apparel and shoes → excluded |
| 23 | Other | Last resort: a real product that fits nowhere above | |

Retired id: 12 (International/Specialty). International foods are labelled by what they are (soy sauce → Condiments,
masa → Baking, Jarritos → Beverages), as the store's own item labels do.
