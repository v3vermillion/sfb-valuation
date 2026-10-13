# Snapshot report — 20261007-182439-full

Status: **hold** (HOLD - previous snapshot stays live)
Checked: 2026-10-13T01:11:12+00:00  |  config hash: 65aa64d97bcb

## Gates
- PASS category_counts — value -, threshold 0.2: no previous snapshot
- PASS departments_complete — value 0, threshold 0.3: 15 departments checked; sizing used
- PASS item_count — value -, threshold 0.9: no previous snapshot
- PASS live_match — value 0.9193, threshold 0.9: 433/471 within 5% (91.9%; exact 412, 87.5%) of the rows Walmart still lists; no longer listed: 29 of 500 (5.8%, not counted as wrong); consumable 92.0% of 200, durable 91.9% of 271; 25 calls
- PASS price_drift — value -, threshold 0.02: no previous snapshot
- FAIL sample_review — value 0.053, threshold 0.05: junk rate 5.3%, systematic junk: no, 16 examples, model claude-sonnet-5-5; notes: Mostly clean consumer goods with sensible names, sizes and flags. Only a few isolated junk rows (auto parts in Baby/Toys, keyword-stuffed marketplace names, wholesale or commercial lots, implausible prices), with no single class large enough to call systematic. The clearest pattern is category mislabeling: Christmas greeting cards under School/Office, koozies and magnets under Sports & Outdoors.
- PASS sentinels — value 0, threshold 0: 114/114 found and priced
- PASS size_parse — value 0.9365, threshold 0.92: 270916/289282 Food rows sized (93.7%): 266389 with a parsed size, 8 sold by the pound, 4519 sold each
- PASS unit_outliers — value 0.03514, threshold -: measure-only: 21595 of 614587 unit-priced rows outside [median/10, median*10] of their category+unit group (3.51%); their per-unit prices are dropped and the rows flagged unit_price_suspect

## Totals
- items kept: 2566573  |  UPCs: 2389686  |  carried over: 0
- UPCs with conflicting prices (>1.5x): 33348

## Kept by department
- Home: 753659 kept of 972354 raw
- Toys: 317995 kept of 512774 raw
- Food: 292988 kept of 315794 raw
- Beauty: 189615 kept of 204670 raw
- Office Supplies: 180906 kept of 667366 raw
- Baby: 165687 kept of 180009 raw
- Pets: 161608 kept of 236558 raw
- Health and Medicine: 152652 kept of 173937 raw
- Party & Occasions: 150392 kept of 242299 raw
- Household Essentials: 68970 kept of 76111 raw
- Personal Care: 66790 kept of 83207 raw
- Premium Beauty: 52016 kept of 54797 raw
- Home Improvement: 8594 kept of 13979 raw
- Seasonal: 4690 kept of 6248 raw
- Pharmacy: 11 kept of 11 raw

## Rejects by reason
- media: 376886
- durable_without_upc: 204365
- durable_over_cap: 195921
- no_price: 156250
- apparel: 128860
- marketplace: 50238
- pet_bed: 20484
- footwear: 11434
- test_listing: 10803
- store_display: 5249
- alcohol: 4874
- no_name: 3311
- food_without_upc_or_size: 1910
- large_equipment: 1332
- tobacco: 1017
- placeholder_no_barcode: 370
- placeholder_price: 132
- duplicate: 105

## Flags
- no_size: 1480028
- sold_each: 28558
- unit_price_suspect: 21595
- placeholder: 19831
- size_conflict: 17795
- pack_resolved: 13102
- retired_upc: 11931
- discontinued: 6274
- pack_truncated: 3113
- price_withheld: 2048
- promo_price: 621
- name_filled: 447
- upc_check_digit: 108

## Plausible price range by department (outside it the price is withheld)

| department | low | high | 99th percentile |
|---|---|---|---|
| Baby | $0.10 | $2,500.00 | $688.09 |
| Beauty | $0.10 | $822.85 | $164.57 |
| Food | $0.10 | $500.00 | $107.27 |
| Health and Medicine | $0.10 | $2,181.25 | $436.25 |
| Home | $0.10 | $478.25 | $95.65 |
| Home Improvement | $0.10 | $485.00 | $97.00 |
| Household Essentials | $0.10 | $500.00 | $214.39 |
| Office Supplies | $0.10 | $484.70 | $96.94 |
| Party & Occasions | $0.10 | $438.75 | $87.75 |
| Personal Care | $0.10 | $994.55 | $198.91 |
| Pets | $0.10 | $1,999.95 | $399.99 |
| Pharmacy | $0.10 | $20.00 | $4.00 |
| Premium Beauty | $0.10 | $1,377.80 | $275.56 |
| Seasonal | $0.10 | $384.95 | $76.99 |
| Toys | $0.10 | $489.95 | $97.99 |

## Withheld prices (2048): valued at an equivalent instead

| department | item | Walmart price | why | valued at | how |
|---|---|---|---|---|---|
| Baby | 809056600 Buy Mickey & Minnie Mouse Convertible Car Seats Together for 30% OFF! | $999,379.00 | above range | $112.18 | comparable item: Buy Mickey & Minnie Mouse Convertible Car Seats To |
| Baby | 192389892 SUP 3YR GMS E-CLASS 24X7 FOR 250 NODES | $15,169.61 | above range | $23.00 | median price of its category |
| Baby | 900000274 CISCO CERT REFURB GSR10-CSC CISCO WRTY NO RETURNS | $9,661.51 | above range | $23.00 | median price of its category |
| Baby | 135384786 F.01U.303.355 DSA E-SERIES SHELF 60X4TB 4HR PDY 12MO | $6,026.59 | above range | $23.00 | median price of its category |
| Baby | 54499333 nuLOOM Hand Knotted Nepalese Milton Trellis Rug 9' x 12' Grey Rectangl | $5,023.50 | above range | $34.29 | median price of the same kind of item |
| Baby | 534858238 Fab Fours GR3000-1 Grumper Grill/Front Bumper; 2 Stage Black Powder Co | $4,071.01 | above range | $33.23 | median price of the same kind of item |
| Baby | 54499331 nuLOOM Hand-Knotted Nepalese Milton Trellis Area Rug | $3,597.45 | above range | $195.28 | comparable item: nuLOOM ACR129A Trellis Area Rug - Slate |
| Baby | 1132456429 Evolur Nursery Essentials Bundle of Madison 5-in-1 Convertible Crib, M | $3,376.15 | above range | $150.51 | median price of the same kind of item |
| Baby | 758381131 Tripplite Uv Sterilization And Cart, For 32 Devices, 34.8 X 21.6 X 42. | $3,326.56 | above range | $23.00 | median price of its category |
| Baby | 175823083 Powerware Start-Up Service - installation / configuration | $3,255.20 | above range | $1,242.85 | comparable item: Powerware Start-Up Service - installation / config |
| Baby | 534120574 1YR RNWL LSS XTMV LARGE OFFICE | $3,130.70 | above range | $361.62 | comparable item: 3YR LSS RNWL XTMV SMALL OFFICE |
| Baby | 118777665 Powerware Start-Up Service - insurance - on-site | $2,981.35 | above range | $2,147.66 | comparable item: Powerware Start-Up Service - insurance - on-site |
| Baby | 645400027 72" STANDING GIRAFFE PLUSH, Case of 10 | $2,940.00 | above range | $14.75 | median price of the same kind of item |
| Baby | 43466657 Nourison 2000 Collection Area Rug | $2,776.92 | above range | $49.99 | comparable item: Fun Rugs Fun Time Collection Area Rug-Size:39" x 5 |
| Baby | 5079841465 ACME Brancaster Accent Chair w/Swivel, Red Top grain Leather | $2,734.00 | above range | $33.03 | median price of the same kind of item |
| Baby | 570604715 Top End Excelerator Handcycle Car Seat, Red | $2,696.00 | above range | $128.00 | median price of the same kind of item |
| Baby | 46500753 Modway Headway Wood Bookshelf in Brown | $2,662.50 | above range | $23.00 | median price of its category |
| Baby | 2682348132 Evolur Nursery Essentials Bundle of Julienne 5-in-1 Convertible Crib,  | $2,599.99 | above range | $150.51 | median price of the same kind of item |
| Baby | 2775170562 Evolur Nursery Essentials Bundle of Julienne 5-in-1 Convertible Crib,  | $2,599.99 | above range | $150.51 | median price of the same kind of item |
| Baby | 15670420617 Enfamil NeuroPro Baby Formula, Triple Prebiotic Immune Blend with 2'FL | $2.35 | far below comparable items | $172.30 | comparable item: Enfamil NeuroPro Baby Formula, Milk-Based Infant N |
| Baby | 177121398 Pampers Swaddlers Diapers (Size N, 162 Count) | $0.98 | far below comparable items | $49.25 | comparable item: Pampers Swaddlers Diapers Size 3 162 count |
| Baby | 395706269 Neocate SyneoTM Infant, 14.1 oz / 400 g (Case of 4 cans) | $0.98 | far below comparable items | $79.34 | median per-unit price of comparable items |
| Baby | 887143439 Pampers Cruisers Diapers, Size 7, 84 ct. | $0.98 | far below comparable items | $41.60 | comparable item: Pampers Cruisers Diapers, Size 6, 84 Diapers |
| Baby | 20889965927 Revolve360 Extend All-in-One Rotating Car Seat, Gray | $0.03 | below range | $439.98 | comparable item: Revolve360 Extend All-in-One Rotating Car Seat, Gr |
| Baby | 16513490 J.L. Childress Co. Bonus Packing Pod | $0.02 | below range | $63.99 | comparable item: J.L. Childress Elite Car Seat Travel Bag with Bonu |
| Baby | 113947008 SAFETY 1ST READY SET WALK WALKER DISPLAY RILEY | $0.01 | below range | $44.52 | comparable item: Safety 1st Ready, Set, Walk! 2.0 Developmental Wal |
| Baby | 136002960 Kolcraft Foam Crib and Toddler Mattress - Display Crib Mattress | $0.01 | below range | $60.00 | comparable item: Dream on Me 5" Crib & Toddler Foam Mattress |
| Baby | 160512190 Munchkin Display Baby Swing | $0.01 | below range | $34.99 | median price of the same kind of item |
| Baby | 161020793 Graco Hayden Crib Short Rail Display | $0.01 | below range | $148.33 | comparable item: Graco Hayden Crib Espresso |
| Baby | 191814060 KidsEmbrace Marvel Spider-Man Combination Harness Booster Car Seat | $0.01 | below range | $39.99 | comparable item: KidsEmbrace Backless Booster Car Seat, Marvel Spid |
| Baby | 220527514 Graco SnugRide SnugFit LX Infant Car Seat, Nash, 1 Count | $0.01 | below range | $219.99 | comparable item: Graco SnugRide SnugFit LX Infant Car Seat, Nash, B |
| Baby | 239533703 LF 4IN1 WALKER DS | $0.01 | below range | $52.49 | median price of the same kind of item |
| Baby | 335399630 Delta Display Silver Lining Bassinet | $0.01 | below range | $90.24 | comparable item: Delta Children Deluxe Gliding Bassinet, Silver Lin |
| Baby | 336098812 Fisher Price Displayer - Fp Stow'ngo Travel Bassinet | $0.01 | below range | $44.49 | median price of the same kind of item |
| Baby | 347795839 T-fal Rw Xcel 39 Stm Dsp | $0.01 | below range | $23.00 | median price of its category |
| Baby | 357069558 Delta Display Turtle Dove Bassinet | $0.01 | below range | $44.49 | median price of the same kind of item |
| Baby | 370503684 Fisher-Price Whimsical Forest Jumperoo Display | $0.01 | below range | $112.48 | comparable item: Fisher-Price Baby Bouncer Whimsical Forest Jumpero |
| Baby | 418610432 Services Taxable Cvmp | $0.01 | below range | $23.00 | median price of its category |
| Baby | 426072706 Services Taxable Cvmp | $0.01 | below range | $23.00 | median price of its category |
| Baby | 431457144 Ingenuity Full Course 6-in-1 Infant Baby High Chair Ð Unisex, Age Up t | $0.01 | below range | $86.99 | comparable item: Ingenuity Full Course 6-in-1 Infant Baby High Chai |
| Baby | 474417677 Delta Display Pooh Bassinet | $0.01 | below range | $89.97 | comparable item: Delta Winnie The Pooh Rocking Bassinet |
| Baby | 481721192 Delta Display Star Glaze Bassinet | $0.01 | below range | $44.49 | median price of the same kind of item |
| Baby | 490470317 Delta Display Royalton Bassinet | $0.01 | below range | $62.87 | comparable item: Delta Gliding Bassinet |
| Baby | 498636066 Evenflo Ev Everykid Maya 4in1 Maya | $0.01 | below range | $179.00 | comparable item: Evenflo EveryKid 4-in-1 Convertible Car Seat (Maya |
| Baby | 580029219 Graco DuoDiner DLX 6-in-1 Convertible Highchair, Kenton, 25 lbs | $0.01 | below range | $179.00 | comparable item: Graco DuoDiner DLX 6-in-1 Convertible Highchair, K |
| Baby | 582984749 Graco True3Fit LX 3-in-1 Car Seat, Fits 3 Car Seats Across, Bates | $0.01 | below range | $279.98 | comparable item: Graco True3Fit LX 3-in-1 Car Seat, Fits 3 Car Seat |
| Baby | 610905728 Services Non Taxable Cvmp | $0.01 | below range | $23.00 | median price of its category |
| Baby | 613124386 Delta Display Beauty Rest Bassinet | $0.01 | below range | $44.49 | median price of the same kind of item |
| Baby | 643490956 Graco Bassinet Little Lounger Kit Dsp | $0.01 | below range | $65.87 | comparable item: Graco Little Lounger, Kit |
| Baby | 657758008 Storkcraft Horizon 5-in-1 Convertible Crib Shortrail Waterfall Display | $0.01 | below range | $161.98 | comparable item: Storkcraft Horizon 5-in-1 Convertible Baby Crib, W |
| Baby | 669451083 Delta Bassinet Royalton Display | $0.01 | below range | $62.87 | comparable item: Delta Gliding Bassinet |
| Baby | 698084468 Graco Lennon Convertible Crib Display | $0.01 | below range | $192.98 | comparable item: Graco Lennon 4-in-1 Convertible Crib in White |
| Baby | 710698885 Graco Story Customizable 5-in-1 Convertible Crib with Drawer -Swing Ar | $0.01 | below range | $298.97 | comparable item: Graco Story Customizable 5-in-1 Convertible Crib w |
| Baby | 794759139 Services Non Taxable Cvmp | $0.01 | below range | $23.00 | median price of its category |
| Baby | 821806590 Haakaa Silicone Breast Pump Display | $0.01 | below range | $11.65 | comparable item: Haakaa Silicone Breast Pump 4 oz, 1 pk |
| Baby | 831550216 Graco Pack ‘n Play Playard Anywhere Dreamer, Marlo | $0.01 | below range | $139.97 | comparable item: Graco Pack ‘n Play Anywhere Dreamer Playard |
| Baby | 840273301 Delta Display Garden Gate Bassinet | $0.01 | below range | $78.30 | comparable item: Delta Children Gliding Bassinet, Garden Gate |
| Baby | 874842918 TIDAL Premium 4-Month FREE Trial, then $7.99/month - A Walmart Exclusi | $0.01 | below range | $23.00 | median price of its category |
| Baby | 911705862 Delta Display Falling Leave Bassinet | $0.01 | below range | $44.49 | median price of the same kind of item |
| Baby | 936284522 Comotomo 5oz 1pk Disp | $0.01 | below range | $6.19 | median per-unit price of comparable items |
| Baby | 976271340 Delta Display Peterrabbit Bassinet | $0.01 | below range | $62.87 | comparable item: Delta Gliding Bassinet |
| Baby | 1135969168 Safety 1st Quad Wagon DISPLAY - DNP | $0.01 | below range | $349.99 | comparable item: Safety 1st Summit Quad 4 Seater Stroller Wagon |
| Baby | 1155471712 Safety 1st® TriFit All-in-One Car Seat, Iron Ore - DISPLAY DNP | $0.01 | below range | $129.00 | comparable item: Safety 1st TriFit All-in-One Convertible Car Seat |
| Baby | 1178712959 Cosco Kids Easy Elite Slim All-in-One Car Seat, Grey Glyphs - DISPLAY  | $0.01 | below range | $99.00 | comparable item: Cosco Kids Easy Elite Slim All-in-One Convertible  |
| Baby | 1183433378 Cosco Kids Finale 2-in-1 Booster Car Seat, Real Tree Edge - DISPLAY DN | $0.01 | below range | $49.97 | comparable item: Cosco Kids Finale 2-in-1 Booster Car Seat, RealTre |
| Baby | 1215772207 Safety 1st® Greener Baby™ Comfort Ride™ 3-in-1 Booster Car Seat, Seal  | $0.01 | below range | $68.59 | comparable item: Safety 1st Comfort Ride™ 3-in-1 Booster Car Seat,  |
| Baby | 1294023740 Hopscotch Lane Premium Highchair Display, 7 Height Options, Babies and | $0.01 | below range | $24.97 | comparable item: Hopscotch Lane Booster Seat with Tray - Portable F |
| Baby | 1356987429 Bright Starts Wild Vibes Infant to Toddler Rocker Display | $0.01 | below range | $45.97 | comparable item: Bright Starts Wild Vibes Baby Infant to Toddler Ro |
| Baby | 1405199588 Graco Nautilus 2.0 3-in-1 Harness Booster Car Seat, Crane, 1 Count | $0.01 | below range | $189.99 | comparable item: Graco Nautilus 2.0 3-in-1 Harness Booster Car Seat |
| Baby | 1436685344 Britax Willow S Infant Car Seat, Glacier Graphite | $0.01 | below range | $352.99 | comparable item: Britax Willow Brook Baby Travel System, Infant Car |
| Baby | 1440997149 Graco SlimFit LX 3-in-1 Car Seat, Shaw, 1 Count | $0.01 | below range | $640.58 | comparable item: (3 pack) Graco SlimFit LX 3-in-1 Convertible Car S |
| Baby | 1647202526 Cam 2 Dream Duo Dummy Unit - Mint (For Displays) | $0.01 | below range | $23.00 | median price of its category |
| Baby | 1670472294 Safety 1st® Turn and Go 360 All-in-One Car Seat, Black Beauty - DISPLA | $0.01 | below range | $139.99 | comparable item: Safety 1ˢᵗ Grow and Go Sprint All-in-One Convertib |
| Baby | 1673094879 Safety 1st Grow and Go Sprint Modular Travel System DISPLAY - DNP | $0.01 | below range | $229.00 | comparable item: Safety 1st Grow and Go Sprint 6-in-1 Modular Trave |
| Baby | 1835899987 Graco Extend2Fit 3-in-1 Car Seat, Stocklyn, 1 Count | $0.01 | below range | $259.00 | comparable item: Graco Extend2Fit 3-in-1 Car Seat, Stocklyn |
| Baby | 1978846994 Safety 1st® Greener Baby™ Comfort Ride™ Lite Booster Car Seat, Pure Bl | $0.01 | below range | $34.98 | comparable item: Safety 1st Comfort Ride Lite Booster Car Seat, Pur |
| Baby | 2262506362 Safety 1st 360 Degree Smart Baby Cam Monitor Display DNP | $0.01 | below range | $23.00 | median price of its category |
| Baby | 2403234193 DELT SNNY CRB FS DSP | $0.01 | below range | $23.00 | median price of its category |
| Baby | 3037921905 BOB Gear Revolution Flex 3.0, Graphite Black Display | $0.01 | below range | $699.99 | comparable item: BOB Gear Revolution Flex 3.0 Jogging Stroller, Gra |
| Baby | 3367801527 Cosco Kids Pronto! DLX Booster Car Seat, Sonic Diamonds DISPLAY - DNP | $0.01 | below range | $128.00 | median price of the same kind of item |
| Baby | 3605138194 Disney Baby High Chair, Modern Minnie DISPLAY DNP | $0.01 | below range | $70.00 | comparable item: Disney Baby 3D Ultra Full-Size High Chair, Modern  |
| Baby | 3619315448 Safety 1ˢᵗ Step Lite Compact Stroller, Greyhound DISPLAY - DNP | $0.01 | below range | $139.98 | comparable item: Safety 1st Step Lite Compact Stroller, Greyhound,  |
| Baby | 3731304937 Safety 1ˢᵗ OnBoard Insta-LATCH Infant Car Seat, Cowbird DISPLAY - DNP | $0.01 | below range | $362.70 | comparable item: (3 pack) Safety 1st onBoard Insta-Latch Infant Car |
| Baby | 3909159126 Safety 1st 360 Spinning High Chair, Soft Ash DISPLAY DNP | $0.01 | below range | $69.99 | median price of the same kind of item |
| Baby | 5022870899 Spectra S1 Plus Dummy | $0.01 | below range | $23.00 | median price of its category |
| Baby | 5023829165 Graco Made2Grow 5-in-1 High Chair for Infants and Toddlers, Terrazo, D | $0.01 | below range | $99.00 | comparable item: Graco Made2Grow 5-in-1 Infant Toddler High Chair,  |
| Baby | 5023829634 HALO FLEX 2 BSNT DISP | $0.01 | below range | $23.00 | median price of its category |
| Baby | 5055219241 Graco® Turn2Me™ 3-in-1 Convertible Car Seat, Cambridge, Display, 30 lb | $0.01 | below range | $399.99 | comparable item: Graco Turn2Me 3-in-1 Convertible Car Seat, Brighto |
| Baby | 5055219242 Graco True3Fit LX 3-in-1 Convertible Car Seat ft. Anti-Rebound Bar, Go | $0.01 | below range | $269.99 | comparable item: Graco True3Fit LX 3-in-1 Convertible Car Seat ft.  |
| Baby | 5055219243 Graco Tranzitions 3-in-1 Harness Booster, Black | $0.01 | below range | $139.97 | comparable item: Graco Tranzitions 3-in-1 Harness Booster |
| Baby | 6267503564 Infantino Grow-with-Me 4-in-1 Convertible High Chair, 6-36 Months, Hus | $0.01 | below range | $99.00 | comparable item: Infantino Grow-with-Me 4-in-1 Convertible High Cha |
| Baby | 6528271700 Ford Bronco HighGear Stroller by Bright Starts, Area 51 Blue/Green, In | $0.01 | below range | $88.99 | comparable item: Ford Bronco HighGear Stroller by Bright Starts, Ar |
| Baby | 6620022521 DELT PHOEBE CRIB -Shortrail Display | $0.01 | below range | $150.51 | median price of the same kind of item |
| Baby | 6634552930 DELT PHOEBE CRIB - Fullsize display | $0.01 | below range | $150.51 | median price of the same kind of item |
| Baby | 6755658170 DELT ELLIE CNC - Shortrail display | $0.01 | below range | $23.00 | median price of its category |
| Baby | 6763517247 Baby Trend Trooper™ SLIM 3-in-1 Convertible Car Seat - Desert Tan (Dis | $0.01 | below range | $99.00 | comparable item: Baby Trend Trooper Slim 3-in-1 Convertible Car Sea |
| Baby | 6780503085 DELT ALICE CNC -Shortrail Display | $0.01 | below range | $23.00 | median price of its category |
| Baby | 6794824687 Baby Trend Hybrid SI 3-in-1 Combination Booster Car Seat - Desert Grey | $0.01 | below range | $99.88 | comparable item: Baby Trend Hybrid SI Desert Grey 3-in-1 Combinatio |
| Baby | 7191708580 Bright Starts Wanderlights 2-in-1 Baby Walker, Blue Green, Unisex, Inf | $0.01 | below range | $56.00 | comparable item: Bright Starts Wanderlights 2-in-1 Baby Walker for  |
| Baby | 7198609570 Baby Einstein Kick & Snooze 3-in-1 Foldable Playard with Bassinet and  | $0.01 | below range | $189.99 | comparable item: Baby Einstein Kick & Snooze 3-in-1 Foldable Playar |
| Baby | 7204919338 Ingenuity Proper Positioner Create Up! Multi-Mode Folding High Chair - | $0.01 | below range | $184.00 | comparable item: Ingenuity Proper Positioner Create Up! Multi-Mode  |
| Baby | 7206807798 Ingenuity Tummy-to-Toes 6-in-1 Milestone Center, Unisex, For Ages 0-48 | $0.01 | below range | $23.00 | median price of its category |
| Baby | 7328716805 Stride Quick-Fold Playard with Hanging Bassinet - Desert Grey (Display | $0.01 | below range | $39.00 | comparable item: Baby Trend Comet Quick-Fold Playard with Full-Size |
| Baby | 7328867970 Baby Trend Simply Smart Playard with Fold Assist Technology - Shale Gr | $0.01 | below range | $125.00 | comparable item: Baby Trend Simply Smart 2.0 Nursery Center Playard |
| Baby | 7384266217 Little Partners® Grow ‘N Stow Folding Learning Tower® Display | $0.01 | below range | $79.00 | comparable item: Little Partners Grow N Stow Folding Learning Tower |
| Baby | 7771100000 Baby Trend Navigator 2-in-1 Stroller Wagon - Desert Tan (Display) | $0.01 | below range | $175.99 | comparable item: Baby Trend Navigator 2-in-1 Stroller Wagon - Deser |
| Baby | 7773155964 Baby Trend Sit N' Stand® Double 2.0 Stroller - Desert Tan (Display) | $0.01 | below range | $179.99 | comparable item: Baby Trend Sit N' Stand Double Stroller, Desert Bl |
| Baby | 7777903725 Baby Trend Quest 2-in-1 Stroller Wagon - Desert Black (Display) | $0.01 | below range | $299.00 | comparable item: Baby Trend Quest 3-in-1 Stroller Wagon |
| Baby | 7783620903 Baby Trend EZ Ride Stroller Travel System with EZ-Lift™ Infant Car Sea | $0.01 | below range | $159.00 | comparable item: Baby Trend EZ Ride Travel System (with EZ-Lift™ In |
| Baby | 7833409505 Ingenuity Trio Foldaway 6-in-1 Baby High Chair, 6 Ways to Use, 6M-5Y | $0.01 | below range | $89.99 | comparable item: Ingenuity Trio Foldaway 6-in-1 Baby High Chair, 6  |
| Baby | 9762112486 BABY TREND COVER ME 4-in-1 CONVERTIBLE CAR SEAT DISPLAY - DESERT BLUE | $0.01 | below range | $179.00 | comparable item: Baby Trend Cover Me Convertible Car Seat w/Canopy, |
| Baby | 10141424565 DISPLAY Alpha Set 2025 v10 | $0.01 | below range | $23.00 | median price of its category |
| Baby | 11927966659 DISPLAY Graco® SnugRide® 35 Lite LX Rear Facing Infant Car Seat, Studi | $0.01 | below range | $149.00 | comparable item: Graco SnugRide Lite LX Infant Car Seat, Studio, Bl |
| Baby | 11943171366 DISPLAY Graco Modes Trio Travel System, Hemlock, Unisex, 32.41 lbs, Di | $0.01 | below range | $319.00 | comparable item: Graco Modes Trio Travel System, Hemlock, Black |
| Baby | 11963307202 DISPLAY Graco SnugRide 35 LX Rear Facing Infant Car Seat, Elko, Displa | $0.01 | below range | $125.00 | comparable item: Graco SnugRide LX Infant Car Seat, Elko, 1 Count |
| Baby | 11963307204 DISPLAY Graco SnugRide Snugfit 35 LX Rear Facing Infant Car Seat, Nash | $0.01 | below range | $219.99 | comparable item: Graco SnugRide SnugFit LX Infant Car Seat, Nash, B |
| Baby | 16690701760 HUGGIES VERTICAL RACK V2 NC CUCUMBER | $0.01 | below range | $23.00 | median price of its category |
| Baby | 16745306619 HUGGIES VERTICAL RACK V2 NC SENSITIVE | $0.01 | below range | $23.00 | median price of its category |
| Baby | 16888455513 Evenflo Shyft Intuiti+ Travel System featuring Revolve180 LiteMax NXT  | $0.01 | below range | $779.00 | comparable item: Evenflo Shyft Intuiti+ Travel System Featuring Rev |
| Baby | 16899467742 EV Eris one hand playard with Bassniet | $0.01 | below range | $229.99 | comparable item: Evenflo Eris One-Hand Playard with Bassinet (Coast |
| Baby | 16909773606 MC CASSIA SWING DISPLAY | $0.01 | below range | $229.99 | comparable item: Maxi-Cosi Cassia Swing, Essential Blush |
| Baby | 16916824129 MC MINLA HIGHCHAIR DISPLAY | $0.01 | below range | $69.99 | median price of the same kind of item |
| Baby | 16933400562 Maxi Cosi Kori Rocker Display, Gray | $0.01 | below range | $139.99 | comparable item: Kori 2-in-1 Rocker |
| Baby | 16947762891 Maxi Cosi Swift Play Yard, Gray Display | $0.01 | below range | $269.00 | comparable item: Maxi-Cosi Swift Play Yard, On Safari Gray |
| Baby | 16954508271 Jeep 2seat Wagon | $0.01 | below range | $228.50 | median price of the same kind of item |
| Baby | 17033052481 Ingenuity Chambray Activity Jumper Display | $0.01 | below range | $79.97 | comparable item: Ingenuity Bounce to Bloom 2-in-1 Activity Jumper & |
| Baby | 17033707946 Ingenuity Smooth Strides Chambray Activity Walker Display | $0.01 | below range | $44.94 | comparable item: Ingenuity Smooth Strides Activity Walker - Develop |
| Baby | 17036613911 Evenflo LiteMax NXT Rear-Facing Lightweight Preemie and Infant Car Sea | $0.01 | below range | $299.99 | comparable item: Evenflo LiteMax NXT Infant Car Seat, Quartz |
| Baby | 19898761421 Graco® EasyTurn 360 2-in-1 Convertible Car Seat, Solae DISPLAY | $0.01 | below range | $279.99 | comparable item: Graco EasyTurn 360 2-in-1 Convertible Car Seat, So |
| Beauty | 602860719 Coppertone 780pc Cp Full Mix Pa | $6,436.60 | above range | $11.35 | median price of its category |
| Beauty | 647056215 Gar Generic 548pcskincare Bts 2 | $5,725.30 | above range | $793.80 | comparable item: Gar Generic Apr 22 Miclr Ec Pdqs |
| Beauty | 142184954 Neutrogena 492pc Ntg Sun Flex | $5,119.20 | above range | $11.35 | median price of its category |
| Beauty | 154273054 St. Ives 547pc Skincare Bts | $3,598.19 | above range | $119.14 | median per-unit price of comparable items |
| Beauty | 783175083 Spa Sciences 108pc Ss Beauty Tool | $3,461.00 | above range | $30.72 | comparable item: L.A. COLORS 45 Pc Box Of Beauty |
| Beauty | 258058226 License 480pcwmd31maskmed | $3,345.60 | above range | $11.35 | median price of its category |
| Beauty | 835624260 Maybelline New York 400pcmay Ve Rocket | $2,916.28 | above range | $13.74 | comparable item: Mayb Superstay Maybelline New York. |
| Beauty | 508277717 Neutrogena 274pc Ntg Sun Hfplt | $2,630.58 | above range | $11.35 | median price of its category |
| Beauty | 887770632 Lp Generic 244pc Lash Paradise | $2,586.94 | above range | $412.57 | median per-unit price of comparable items |
| Beauty | 101095969 Maybelline New York 298pc May Eye Lip Pl | $2,586.20 | above range | $11.35 | median price of its category |
| Beauty | 17752616459 (198 pack) Wewdigi Women Man Professional Nail, Pedicure Kit, Gift Man | $2,385.90 | above range | $9.59 | median price of the same kind of item |
| Beauty | 546994565 Fructis 402pc Gar Oct Hair D | $2,283.12 | above range | $11.35 | median price of its category |
| Beauty | 890416743 Gelish 18G Professional Salon Gel Nail Polish Dry Cure LED Light (12 P | $2,267.65 | above range | $7.92 | median price of the same kind of item |
| Beauty | 795838688 Lp Generic 190pceye Bestsell S | $2,234.17 | above range | $14.28 | comparable item: Lp Generic L'oreal Paris Visi. |
| Beauty | 21343964 Panamax 7500-PRO Line Conditioner | $2,099.95 | above range | $3.47 | comparable item: P & G Pantene Pro V Conditioner, 16.2 oz |
| Beauty | 707566900 Wet N Wild 1072pc Wnw Hal Palle | $2,066.84 | above range | $11.35 | median price of its category |
| Beauty | 5555593452 (100 pack) Blackhead Remover Vacuum,Upgraded Facial Pore Cleaner,Elect | $2,050.00 | above range | $20.50 | comparable item: Blackhead Remover Vacuum,Upgraded Facial Pore Clea |
| Beauty | 423837336 Maybelline New York 206pc May Lip Fce Tw | $2,002.68 | above range | $11.35 | median price of its category |
| Beauty | 1380347751 L'oreal Paris Hol22 Eye+face Ms | $1,987.90 | above range | $11.35 | median price of its category |
| Beauty | 715800912 Paris Hilton 98pc Qkh20 Fragrance | $1,958.04 | above range | $11.97 | median price of the same kind of item |
| Beauty | 959752716 Lp Generic 192pc 2020 Halloween | $1,935.27 | above range | $11.35 | median price of its category |
| Beauty | 526820930 Lp Generic 179pc Mar Eye Lip Ms | $1,925.22 | above range | $11.35 | median price of its category |
| Beauty | 5555593454 (78 pack) Blackhead Remover Pore Vacuum,Electric Facial Blackhead Suct | $1,877.46 | above range | $24.07 | comparable item: Blackhead Remover Pore Vacuum,Electric Facial Blac |
| Beauty | 2892696662 Lp Generic Lp Core Hp | $1,834.46 | above range | $14.28 | comparable item: Lp Generic L'oreal Paris Visi. |
| Beauty | 412483681 Mayb Generic 191pc May Lip/eye | $1,759.94 | above range | $11.35 | median price of its category |
| Beauty | 691039639 Gar Fructis 342pcgar Apr Demo S | $1,754.16 | above range | $11.35 | median price of its category |
| Beauty | 2336364153 Mayb Generic 185pc May Grt Hit Es | $1,727.36 | above range | $11.35 | median price of its category |
| Beauty | 18587762507 (24 pack) RoC Skincare Retinol Correxion Deep Wrinkle Anti-Aging Night | $1,656.00 | above range | $66.85 | median per-unit price of comparable items |
| Beauty | 422953902 Mayb Generic 145pcmay Tat Brw Pom | $1,616.58 | above range | $11.35 | median price of its category |
| Beauty | 954314870 Body Fantasies 470pcpdc 1/2 Stack | $1,616.24 | above range | $11.35 | median price of its category |
| Beauty | 766682090 Coppertone 180pc Ct 8.3oz 2020 | $1,614.60 | above range | $323.00 | comparable item: Coppertone 36pc2019 Wmt Ct Glo |
| Beauty | 105739799 Coppertone 166pc Cp 2020 Cp 166 | $1,570.54 | above range | $323.00 | comparable item: Coppertone 36pc2019 Wmt Ct Glo |
| Beauty | 18552274365 (100 pack) Hairitage Good Vibes Jade Comb Scalp Massager | Jade Hair T | $1,499.00 | above range | $14.99 | comparable item: Hairitage Good Vibes Jade Comb Scalp Massager | Ja |
| Beauty | 841069447 Nyx Professional 153pc Nyx Halloween | $1,488.36 | above range | $11.35 | median price of its category |
| Beauty | 341886285 Maybelline New York 150pc May Eye Fce Tw | $1,479.00 | above range | $11.35 | median price of its category |
| Beauty | 772173634 Mayb Generic 162pc May Face/lip | $1,408.00 | above range | $11.35 | median price of its category |
| Beauty | 894448408 Mayb Generic 200pc May Mas Gwp Tw | $1,386.80 | above range | $11.35 | median price of its category |
| Beauty | 5556382839 (170 pack) Makeup Brushes, 20 PCS Makeup Brush Set tools Make-up Toile | $1,377.00 | above range | $8.10 | comparable item: Makeup Brushes, 20 PCS Makeup Brush Set tools Make |
| Beauty | 763438902 Mayb Generic 162pc May Face/lip | $1,354.00 | above range | $11.35 | median price of its category |
| Beauty | 5306596032 Dinan D980-0029 Performance Front Lip - Gloss Twill Carbon Fiber | $1,348.95 | above range | $11.35 | median price of its category |
| Beauty | 342895014 Mayb Generic 172pc May Grt Lsh Es | $1,345.68 | above range | $11.35 | median price of its category |
| Beauty | 559853619 Mayb Generic 142pc May Lip/eye | $1,299.96 | above range | $11.35 | median price of its category |
| Beauty | 109923267 L'oreal Paris 138pc Noir Balm Es | $1,288.08 | above range | $493.65 | comparable item: L'oreal Paris 45pc Prec Pen |
| Beauty | 18611154548 (72 pack) Mean Girls x Revolution The Plastics Mini Set | $1,233.36 | above range | $22.84 | comparable item: Mean Girls x Revolution Fetch Brush Set with Hair  |
| Beauty | 735060671 Reina Rebelde On Your Face Contour + Color Trio - Adorada - 7 g / 0.25 | $1,230.48 | above range | $12.41 | median price of the same kind of item |
| Beauty | 624381025 Maybelline New York 130pc May Lip Eye Tw | $1,208.86 | above range | $11.35 | median price of its category |
| Beauty | 145051026 Gelish 18G Professional Salon Gel Nail Polish Dryer Cure LED Light (6  | $1,204.99 | above range | $59.43 | median per-unit price of comparable items |
| Beauty | 380049269 Clean & Clear 163pc Ntg Cc Acne Tw | $1,158.07 | above range | $43.36 | median per-unit price of comparable items |
| Beauty | 340386189 SHANY Light-Up Makeup Mirror Station and Storage - Rolling Cosmetics C | $1,155.24 | above range | $17.44 | median price of the same kind of item |
| Beauty | 3253195587 C7 23 WM GAR Fructis BTS HPLLT | $1,136.40 | above range | $6.97 | comparable item: Fructis Bts Kit Sleek & Shine |
| Beauty | 926957735 Neutrogena 228pc Ntg Mur Tower | $1,124.04 | above range | $11.35 | median price of its category |
| Beauty | 676594322 Gelish Gel Nail Polish Starter Kit, 9 mL with 5 Colors & LED Light (12 | $1,099.99 | above range | $67.88 | median per-unit price of comparable items |
| Beauty | 176172084 Lp Root Rescue 60pcrcu Twin Pack Sk | $1,078.20 | above range | $355.10 | comparable item: Lp Root Rescue 30pclag Rcu + Pen Sk |
| Beauty | 471561198 Speed Queen DR3000WE Electric 27 Inch Dryer White | $1,062.50 | above range | $11.35 | median price of its category |
| Beauty | 55092152 The New Clean Ultimate Promo Kit by Unwash - 97 Pc Kit 12 Comb, Rethin | $1,057.33 | above range | $14.21 | median per-unit price of comparable items |
| Beauty | 710293238 Tom Ford Rose Prick Eau de Parfum for Women 250ml/8.5oz | $1,004.00 | above range | $56.34 | comparable item: Lolita Lempicka, Eau de Parfum for Women, 1.7 fl o |
| Beauty | 616485025 SHANY Light-Up Makeup Mirror Station and Storage - Rolling Cosmetics C | $999.96 | above range | $17.44 | median price of the same kind of item |
| Beauty | 258733781 REAL COSMETIC IN TROLLEY, Case of 144 | $997.80 | above range | $576.60 | comparable item: REAL COSMETIC IN TROLLEY, Case of 72 |
| Beauty | 727635381 Lp Generic 79pclor Ap Mascara | $976.08 | above range | $10.38 | comparable item: Lp Generic Loreal Voluminous Shocking Mascara |
| Beauty | 842678013 Real Techniques 225pcholiday Ornamn | $971.43 | above range | $11.35 | median price of its category |
| Beauty | 5885327932 (12 pack) Olaplex No. 5 Bond Maintenance Conditioner 33.8 oz | $921.60 | above range | $14.88 | median price of the same kind of item |
| Beauty | 373328446 L'oreal Paris Glow At Home Cospart | $900.93 | above range | $6.99 | comparable item: Glow at Home with L'Oreal Paris |
| Beauty | 105580296 La Prairie Cellular Cream Platinum Rare, 1 Oz | $895.00 | above range | $520.59 | comparable item: Cellular Eye Cream Platinum Rare by La Prairie for |
| Beauty | 236428945 Neutrogena 105pc Ntg Hb Tower | $886.65 | above range | $11.35 | median price of its category |
| Beauty | 36317809 2009 Ford F150 V8-4.6L/5.4L Triton Single side exit | $884.00 | above range | $11.35 | median price of its category |
| Beauty | 244516071 Real Techniques 239pc Rt/eco Neon Sp | $881.63 | above range | $337.23 | median per-unit price of comparable items |
| Beauty | 1504588149 Mayb Generic 92pc May Bts At Box | $875.68 | above range | $734.16 | comparable item: Mayb Generic 26pc May Ld Liner At |
| Beauty | 581919549 Lp Generic 141pc Elv Drm Lnth S | $875.61 | above range | $700.77 | comparable item: Lp Loreal Ahc 32pc Elv Drm Lnth Sk |
| Beauty | 308150116 100 PC LIP-RAGEOUS LIP BALM, Case of 12 | $869.10 | above range | $6.63 | median price of the same kind of item |
| Beauty | 212629598 Sally Hansen 172pc Sh $4 Nail Abl | $842.54 | above range | $89.77 | comparable item: Sally Hansen Design 3D Nail Sticker - 320 Floral 1 |
| Beauty | 956429434 L'oreal Paris 92pc Paradise Sdk | $824.44 | above range | $493.65 | comparable item: L'oreal Paris 45pc Prec Pen |
| Beauty | 690133887 Garnier Whole Blends Legendary Olive Replenishing Conditioner, 22 Fl.  | $0.50 | far below comparable items | $9.30 | comparable item: Garnier Whole Blends Replenishing Conditioner Lege |
| Beauty | 187150854 Puffy Tray Liner, 1 Fl. Oz. | $0.03 | below range | $37.00 | median per-unit price of comparable items |
| Beauty | 17905401744 e.l.f. SKIN Vitamin C+E+Ferulic Serum, Mini | $0.03 | below range | $19.00 | comparable item: e.l.f. SKIN Glass Slick Serum Stick, 0.63 oz |
| Beauty | 17955356667 e.l.f. SKIN Holy Hydration Clean Freak Daily Cleanser Mini | $0.03 | below range | $11.11 | comparable item: e.l.f. SKIN Holy Hydration! Makeup Melting Cleansi |
| Beauty | 21035105 Reckitt Benckiser Clearasil Perfecta Wash Automatic Face Wash Dispense | $0.02 | below range | $10.40 | comparable item: Clearasil PerfectaWash Automatic Face Wash Dispens |
| Beauty | 107754166 Brightstar Distrib Bb 9700 Skins Pk Db | $0.02 | below range | $11.35 | median price of its category |
| Beauty | 22307114 Olay Prox Gift With Purchase Kit | $0.01 | below range | $11.35 | median price of its category |
| Beauty | 130150129 Floepx Women Nylon Cosmetic Bags Makeup Organizer Storage Bag Pouch Ho | $0.01 | below range | $7.05 | comparable item: Cosmetic Bag for Travel and Makeup, Cosmetic Bag f |
| Beauty | 333019137 Hairitage USA Mini Riser-2021 | $0.01 | below range | $11.35 | median price of its category |
| Beauty | 404125051 Paint 1st Md Mk | $0.01 | below range | $9.19 | median price of the same kind of item |
| Beauty | 596834842 YoaNJYGR Human Curly Hair Wigs for Short Wave Head Wig Brown Bangs Str | $0.01 | below range | $18.77 | median price of the same kind of item |
| Beauty | 840101034 Hairitage Medium Riser 2021 | $0.01 | below range | $11.35 | median price of its category |
| Beauty | 877548387 Tulip 8 Slot 4.25 Oz. Tray Liner, 1 Each | $0.01 | below range | $11.35 | median price of its category |
| Beauty | 14394752581 Manic Panic Empty Display | $0.01 | below range | $8.45 | median per-unit price of comparable items |
| Food | 839235108 (3 pack) (30 Pouches) Alpine Spiced Apple Cider Sugar Free Drink Mix | $3,260,499,999,999,999,868,928.00 | above range | $8.94 | median price of the same kind of item |
| Food | 6703965891 TestProductName ForAutomation | $7,968,296.10 | above range | $6.83 | median price of its category |
| Food | 1229599116 (2 pack) Elite Milk Chocoate Bar, 3.5 oz | $323,376.08 | above range | $6.32 | comparable item: Elite Milk Chocolate Bar, 3.5 Oz |
| Food | 33311307 Elite Milk Chocoate Bar, 3.5 oz | $161,688.04 | above range | $3.16 | comparable item: Elite Milk Chocolate Bar, 3.5 Oz |
| Food | 55292801 Augason Farms Mega Emergency 1 Year Food Supply Everyday Meal Prep Lar | $33,442.23 | above range | $39.99 | comparable item: Augason Farms 5-Day 1-Person Emergency Food Supply |
| Food | 22985176 Augason Farms Deluxe 1-year, 3-person Em | $7,891.64 | above range | $497.03 | comparable item: Augason Farms 6 Month 1 Person Kit |
| Food | 6157452041 CHR Assorted Chocolate Packaged Candy Laydown Bag Full Module, 1536 ct | $6,900.48 | above range | $8.28 | median price of the same kind of item |
| Food | 46893127 Wise Company 4320 Serving Entre And Brea | $5,930.94 | above range | $8.72 | median price of its category |
| Food | 15086713897 754 pc 754 PC 754PCAST STAN | $5,689.76 | above range | $7.82 | median price of its category |
| Food | 5287616040 840 pc 840PCWM HSHY MC 6PK | $5,443.20 | above range | $52.31 | median per-unit price of comparable items |
| Food | 18882608794 1170 pc AST TWIZ 1170CT | $5,405.00 | above range | $148.24 | median per-unit price of comparable items |
| Food | 434253198 (16 pack) (16 Pack) Nugo Nutrition Bar Fiber Delish Blondie Bar, 1.6 O | $5,000.00 | above range | $69.28 | comparable item: Nugo Nutrition Bar Fiber Delish Blondie Bar, 1.6 O |
| Food | 558599556 Hershey Assortment 1496p 12pk Hrshy Bts | $4,727.36 | above range | $25.34 | comparable item: Hershey Assortment Hershey Trunk Or Treat Bag |
| Food | 18767774362 622 pc 622 PC MULTI SMORE | $4,602.00 | above range | $9.00 | median price of its category |
| Food | 26958407 ReadyWise 2160 Serving Package of Long Term Emergency Food Supply | $4,599.99 | above range | $8.72 | median price of its category |
| Food | 864065904 Vistar Cheez-It Crackers - Pack of 12 | $4,566.88 | above range | $4.75 | comparable item: CHEEZ IT ORIG |
| Food | 328559195 (12 pack) (12 Pack) Skinnypop Popcorn Skinny Pop - White Cheddar , 4.4 | $4,528.80 | above range | $32.28 | comparable item: Skinny Pop White Cheddar Popcorn, 4.4 oz (Pack of  |
| Food | 146418972 Nestle Tollhouse 960pcnth Sm Asst Pa | $4,492.80 | above range | $8.72 | median price of its category |
| Food | 26958405 Wise Company Combination Breakfast/Entree & Soup Emergency Food Supply | $4,219.48 | above range | $9.84 | median price of the same kind of item |
| Food | 534245935 4 oz Popcorn Packs Pre-Measured, Movie Theater Style Packets for Popco | $4,185.00 | above range | $1.13 | comparable item: 6 oz Popcorn Packs Pre-Measured, Movie Theater Sty |
| Food | 982136949 Equate Eq Hiperf Cho 192pc | $4,028.00 | above range | $166.31 | median per-unit price of comparable items |
| Food | 420003127 (12 pack) (12 Pack) Bearitos Organic Traditional Refried Beans, 16 Oz. | $3,934.96 | above range | $19.51 | median per-unit price of comparable items |
| Food | 1543564471 Twix 800pcsnickers Fun S | $3,776.00 | above range | $10.00 | comparable item: Twix 800pcsnickers Fun S |
| Food | 741756650 Hershey 816pchsy Mlk Giant | $3,688.32 | above range | $9.00 | median price of its category |
| Food | 969019574 Hershey Assortment 1220pccandy Mod | $3,635.60 | above range | $11.84 | comparable item: Hershey Assortment Hershey Shapes Varty Box 23.7oz |
| Food | 940366347 M M S 712pcfull $2.78 712 | $3,503.00 | above range | $9.00 | median price of its category |
| Food | 14424814744 Pillsbury Baking Pillsbury 17.5 Oz Sugar Cookie Mix | $3,500.00 | above range | $1.96 | comparable item: Pillsbury Baking Pillsbury 17.5 Oz Sugar Cookie Mi |
| Food | 43803693 Reese's Easter Peanut Butter Egg Candy Snack Bite | $3,317.76 | above range | $12.13 | comparable item: Reese's Easter Peanut Butter Egg Candy, 12 oz, 2 c |
| Food | 35053655 Lindon Farms 4320 Servings Freeze Dried Food Survival Emergency Storag | $3,250.00 | above range | $8.72 | median price of its category |
| Food | 21117218058 (5 pack) Deer Park Spring Water, 25 fl oz, Single Aluminum Bottle | $3,218.40 | above range | $31.56 | comparable item: Deer Park Spring Water, 20 Fl Oz, Single Plastic B |
| Food | 55292803 Augason Farms Deluxe 1-Year 4-Person Emergency Food Supply 336 Large C | $3,032.42 | above range | $123.89 | comparable item: Augason Farms Deluxe 30-Day Emergency Food Supply, |
| Food | 22985173 Augason Farms 1-Year 4-Person Emergency Food Supply | Shelter-in-Place | $2,982.87 | above range | $17.50 | comparable item: Creamy Potato Soup Mix Emergency Food Supply, 36 S |
| Food | 571807977 (10 pack) (10 Pack) Jovial Fig Fruit Filled Cookies, 7 Oz | $2,971.00 | above range | $46.98 | comparable item: Jovial Fig Fruit Filled Cookies, 7 oz, (Pack of 5) |
| Food | 22985175 Augason Farms Superior 1-year, 2-person | $2,940.79 | above range | $50.09 | comparable item: Augason Farms Instant Potatoes 6 Gallon |
| Food | 430929779 Great Value 2304pc Gv Evap Full | $2,810.88 | above range | $8.72 | median price of its category |
| Food | 596291674 Russell Stover 384pcrs Ac Holiday | $2,808.32 | above range | $9.00 | median price of its category |
| Food | 22001496 Augason Farms Basic 4 Person, 1 Year Emergency Food Storage Kit, 330 c | $2,756.63 | above range | $105.08 | comparable item: Augason Farms Breakfast Pack Emergency Food Storag |
| Food | 438604582 Wonderful Pistachios 312pc Wndfl Pist 16z | $2,602.08 | above range | $13.03 | median per-unit price of comparable items |
| Food | 234856138 Planters 350pcplntr Csh Drzl | $2,524.00 | above range | $23.54 | median price of the same kind of item |
| Food | 581982310 Tortrix Creole Sauce Chips 6.3oz - Salsa Criolla (Pack of 40) | $2,473.99 | above range | $9.30 | median price of the same kind of item |
| Food | 18875261780 496 pc 496 PC HSY AST TWIZ | $2,292.00 | above range | $9.00 | median price of its category |
| Food | 239911416 48/24/14z SAUCE MIX (36J/12W) RTD | $2,280.96 | above range | $5.50 | comparable item: Emergency Essentials Alfredo Sauce Mix, 56 oz |
| Food | 19858169379 152 pc 152 PC AST RWB PRTY | $2,256.00 | above range | $135.57 | median per-unit price of comparable items |
| Food | 798529697 Hershey 368pcasst Choc Sub | $2,196.96 | above range | $9.00 | median price of its category |
| Food | 426499493 M And M 432pcm&ms Pn Sup 10 | $2,125.44 | above range | $107.82 | comparable item: M And M 9pcm&ms Pnt Bttr Sup |
| Food | 313611938 M And M 432pcm&m's Mixed Fu | $2,125.00 | above range | $9.00 | median price of its category |
| Food | 161833734 Jolly Rancher Original Fruit Chews, (Pack of 12) | $2,090.88 | above range | $7.72 | comparable item: Jolly Rancher Fruit Chews, 12.2 Oz. |
| Food | 55292802 Augason Farms Variety Emergency Food Supply 40-Pail Kit | $2,054.35 | above range | $165.44 | comparable item: Augason Farms Emergency Food Supply Variety Pack,  |
| Food | 839640807 (1200 pack) (12 Pack) Inko’S Tea, Blueberry White, 16 fl oz | $2,021.15 | above range | $14.92 | median price of the same kind of item |
| Food | 730842425 (6 pack) Cherrybrook Kitchen - Cookie Mix - Chocolate Chip - Case Of 6 | $2,000.00 | above range | $35.44 | comparable item: Cherrybrook Kitchen Chocolate Chip Cookie Mix, 14. |
| Food | 409653501 Wonderful Pistachios 192pc192 Wfl Combo | $1,992.96 | above range | $14.96 | median price of the same kind of item |
| Food | 6435154189 Wonderful Pistachios 192pc | $1,954.56 | above range | $84.10 | comparable item: Goldfish 20ct 48pc |
| Food | 19964657349 288 pc Lindt Spring HPLT | $1,953.00 | above range | $9.00 | median price of its category |
| Food | 381157725 Tortrix Creole Sauce Chips 6.3oz - Salsa Criolla (Pack of 32) | $1,918.51 | above range | $9.30 | median price of the same kind of item |
| Food | 19429757000 344 pc 344 PC M&MS MXD SUP | $1,885.00 | above range | $11.36 | median price of the same kind of item |
| Food | 55292804 Augason Farm?s Premium Emergency 1-Year Food Supply (1 Person), 138 No | $1,841.14 | above range | $9.99 | median price of the same kind of item |
| Food | 2650681318 Ghirardelli 256pcholiday Half P | $1,838.08 | above range | $9.00 | median price of its category |
| Food | 16557267815 MIXED VARIETY 180CT HPLT D1 WM IDM | $1,793.00 | above range | $164.25 | median per-unit price of comparable items |
| Food | 467767668 Starbucks 140pcsbux Holiday 1 | $1,776.40 | above range | $8.72 | median price of its category |
| Food | 163218569 Starbucks 140pcsbux Fall Disp | $1,753.08 | above range | $8.72 | median price of its category |
| Food | 2091903585 Ghirardelli 512pcholiday Full P | $1,751.91 | above range | $9.00 | median price of its category |
| Food | 16748757514 WM MARS MXD SHR SZ SUP | $1,751.52 | above range | $9.00 | median price of its category |
| Food | 16313774749 MULTI BRAND COOKIES 425 CT | $1,686.50 | above range | $8.10 | median price of the same kind of item |
| Food | 17093309611 Quaker Instant Oatmeal Variety, 48 Count Display | $1,653.12 | above range | $15.99 | comparable item: Quaker Instant Oatmeal, Flavor Variety, 52 Ct |
| Food | 26958406 Wise Foods 1080 Serving Package of Long Term Emergency Food Supply Fre | $1,641.18 | above range | $8.72 | median price of its category |
| Food | 15023971249 ND TR SUB HALF PALL WM 400/9.2oz SHP | $1,588.00 | above range | $4.93 | median per-unit price of comparable items |
| Food | 378296257 Great Value 1296pc Gv Evap Half | $1,581.12 | above range | $8.72 | median price of its category |
| Food | 19858169536 324 pc M&MS SUP WM RWB 324HPLT IDM | $1,549.00 | above range | $11.36 | median price of the same kind of item |
| Food | 632220565 Homestyle Noodles 420pc Essenhaus Ndls | $1,528.80 | above range | $9.92 | median price of the same kind of item |
| Food | 471069326 Pringles 760pcprg 4flv Modx7 | $1,520.00 | above range | $5.53 | median price of the same kind of item |
| Food | 20021974375 400 pc NERDS TROLLI RWB HPLT 400CT | $1,510.00 | above range | $93.68 | median per-unit price of comparable items |
| Food | 14588707082 PEPPERIDGE FARM MILANO COOKIES | $1,505.90 | above range | $3.72 | comparable item: (3 Pack) Pepperidge Farm Milano Orange Cookies, 7  |
| Food | 155481523 Kamado Joe Big Joe I 24 in. Charcoal Grill in Red with Cart, Side Shel | $1,499.99 | above range | $33.23 | median price of the same kind of item |
| Food | 796141906 Nab Classics 160pcnabisco Ss 20ct | $1,497.00 | above range | $16.66 | median per-unit price of comparable items |
| Food | 523662798 Frito-lay 580pc Mixed Hot Spcy | $1,496.40 | above range | $0.72 | comparable item: BAKEN-ETS HOT & SPCY |
| Food | 105412330 Pringles 728pcprg Core 4 Sup | $1,456.00 | above range | $3.73 | median per-unit price of comparable items |
| Food | 833986669 PEPPERIDGE FARM STUFFING HERB AND CORN | $1,447.20 | above range | $4.03 | comparable item: Pepperidge Farm Corn Bag Stuffing 16 Oz |
| Food | 847901772 Pepperidge Farm 540pc Cube/herb/crn MT2025 | $1,447.20 | above range | $326.05 | median per-unit price of comparable items |
| Food | 601148686 Tortrix Creole Sauce Chips 6.3oz - Salsa Criolla (Pack of 24) | $1,442.12 | above range | $91.82 | comparable item: Tortrix Tacos Creole Sauce 6.34 oz - Salsa Criolla |
| Food | 476494023 Freshness Guaranteed 144pc 20z Value Nuts | $1,437.12 | above range | $10.05 | comparable item: Great Value Mixed Nuts, 17 oz |
| Food | 18849322454 360 pc 360 PC HSY SS DUMP B | $1,411.00 | above range | $76.57 | median per-unit price of comparable items |
| Food | 704554090 Chip Granola Bars, 60 Ct.Net Wt 52.8 Oz | $1,353.99 | above range | $9.96 | median price of the same kind of item |
| Food | 3250449556 PEPPERIDGE FARM GOLDFISH CRACKERS VARIETY | $1,340.64 | above range | $5.98 | comparable item: PEPPERIDGE FARM CRACKERS VARIETY |
| Food | 214736119 Kathy Kaye Popcorn Ball Full | $1,319.04 | above range | $17.95 | comparable item: Popcorn Ball |
| Food | 55702761 Augason Farms 1-Year 1-Person Emergency Food Storage Pail Kit - 12 Cou | $1,294.78 | above range | $105.08 | comparable item: Augason Farms Breakfast Pack Emergency Food Storag |
| Food | 55292805 Augason Farms Deluxe Emergency 1-Year Food Supply (1 Person), 98 No. 1 | $1,290.99 | above range | $20.60 | median price of the same kind of item |
| Food | 22001495 Augason Farms 1 Year 1 Person Deluxe Kit | $1,285.14 | above range | $497.03 | comparable item: Augason Farms 6 Month 1 Person Kit |
| Food | 17968304404 258 pc WM GMI(9) HNC/YBC/PROT/CNFC/GRNOLA COMU | $1,272.00 | above range | $155.78 | median per-unit price of comparable items |
| Food | 938172501 Coffee Break Lunch Room Furniture FULLY ASSEMBLED "Ready-To-Use" 3pc G | $1,267.97 | above range | $18.27 | median price of the same kind of item |
| Food | 16608802442 272 pc SK FRT SHRSZ SUP D1 | $1,243.00 | above range | $5.48 | median per-unit price of comparable items |
| Food | 18156803834 252 pc WM GMI (2) SPDLC/LC FS COMU | $1,242.36 | above range | $152.16 | median per-unit price of comparable items |
| Food | 440247522 Atkins 165pcsnack Rtd Vrty | $1,221.20 | above range | $125.64 | comparable item: Atkins 18pcsnack Bar Vrty |
| Food | 29304825 Pacific Foods Organic 7 Grain Non-Dairy Beverage, Original, 32-Ounce,  | $1,219.51 | above range | $49.11 | comparable item: (12 Pack) Pacific Foods Organic Almond Non-Dairy B |
| Food | 51258891 WAL*MART CINNAMON ROLL ICING 42# | $1,217.16 | above range | $167.13 | comparable item: Freshness Guaranteed Mini Cinnamon Rolls, No Icing |
| Food | 295896986 24 PCS PUSH POP CANDY, Case of 24 | $1,208.40 | above range | $8.28 | median price of the same kind of item |
| Food | 18787869979 240 pc JR GUMMIE 240CT | $1,193.00 | above range | $9.00 | median price of its category |
| Food | 18897318444 240 pc AST JR HARD 240CT | $1,193.00 | above range | $83.36 | median per-unit price of comparable items |
| Food | 950136033 Cotail Kit For Tea Lovers | $1,188.99 | above range | $54.99 | comparable item: Tea Lovers Gift |
| Food | 485393064 Heinz Homestyle 420pc Heinz 18oz Gra | $1,184.40 | above range | $6.63 | median per-unit price of comparable items |
| Food | 671278940 Belvita 270pcbvita Fignewt | $1,179.60 | above range | $9.00 | median price of its category |
| Food | 19392617614 270 pc SK GMS MXD SUP WM 270HPLT IDM | $1,141.00 | above range | $127.29 | median per-unit price of comparable items |
| Food | 693494428 Freshness Guaranteed 237pc In-shell Nuts | $1,106.79 | above range | $15.29 | median price of the same kind of item |
| Food | 55292806 Augason Farm’s Deluxe Emergency 1-Year Food Supply (1 Person), 86 #10  | $1,106.58 | above range | $20.60 | median price of the same kind of item |
| Food | 772395557 Frito-lay 248pc Ruff/cheeto | $1,103.54 | above range | $9.00 | median price of its category |
| Food | 405862662 Cheez-it 280pc Chzit 5flvcore | $1,055.60 | above range | $8.64 | median price of the same kind of item |
| Food | 159496165 Sun-Maid® Zante Currants, 10-Oz Box | $1,055.06 | above range | $14.74 | comparable item: (2 pack) Sun-Maid® California Sun-Dried Zante Curr |
| Food | 904428226 Starbucks 120pccold Brew 120c | $1,051.44 | above range | $13.94 | median price of its category |
| Food | 246758264 Idahoan® Foods 820pcidhn 4oz Fm Ha | $1,041.40 | above range | $1.67 | median per-unit price of comparable items |
| Food | 129524115 Perugina Italian Baci, Classic Dark, 2 Oz | $1,035.00 | above range | $2.57 | comparable item: Divine Chocolate Dark Chocolate Classic 3.5 Oz |
| Food | 19458318044 360 pc AMOS PEELERZ HLPL 360CT | $1,029.60 | above range | $84.31 | median per-unit price of comparable items |
| Food | 17672572076 Everyday Popcorn Ball | $1,008.00 | above range | $17.95 | comparable item: Popcorn Ball |
| Food | 14424968800 Great Value Instant Mashed Pot 13.75oz | $1,000.00 | above range | $255.24 | comparable item: Great Value Instant Mashed Pot 13.75oz |
| Food | 14425262253 Great Value Chicken Stuffing 6oz | $1,000.00 | above range | $0.83 | comparable item: (12 pack) Great Value Chicken-Flavored Stuffing Mi |
| Food | 111586720 98.5-00 DODGE JUICE CTS2 | $999.95 | above range | $8.94 | median price of the same kind of item |
| Food | 305900439 (6 pack) (6 Pack) Sweet Leaf English Toffee Sweet Drops, 2 Oz | $999.00 | above range | $11.98 | comparable item: English Toffee, 10 Oz. |
| Food | 741628277 Tortrix Creole Sauce Chips 6.3oz - Salsa Criolla (Pack of 16) | $997.90 | above range | $61.22 | comparable item: Tortrix Tacos Creole Sauce 6.34 oz - Salsa Criolla |
| Food | 952570410 Kellogg 144pc3 Flv Pllw Bag | $987.84 | above range | $392.16 | comparable item: Kellogg 300pcrkt 3 Flv Ss 1 |
| Food | 17752816463 (30 pack) Fire & Smoke Society Mixed Spices & Seasonings (4 Pack), BBQ | $950.40 | above range | $8.40 | median price of the same kind of item |
| Food | 5311559925 Kellogg's Cheez It Crackers 6 Flavors | $948.50 | above range | $8.99 | comparable item: Kellogg's Cheez It Crackers Snack Mix 48oz |
| Food | 858286776 Cheerios 192pcmultigran Cher | $946.56 | above range | $7.63 | median price of the same kind of item |
| Food | 16220651243 Kellogg's Pop-Tarts 5 Flavors | $943.20 | above range | $7.36 | comparable item: Kellogg's Strawberry Pop-Tarts, 16 ct (Pack of 2) |
| Food | 906664211 Fruity Pebbles and Cocoa Pebbles Large Size Variety Pack - Gluten Brea | $935.99 | above range | $14.08 | comparable item: (6 pack) Post Fruity PEBBLES Cereal, Fruity Kids C |
| Food | 55203432 Russell Stover Assorted Fine Chocolates, 7 oz | $933.70 | above range | $6.87 | comparable item: Russell Stover Fine Assorted Chocolates, 5 Oz. |
| Food | 931399672 General Mills 144pcgmi(3)acc/ckc/ | $925.11 | above range | $8.72 | median price of its category |
| Food | 569002877 San Pelegrino Sp 11.15 8ct Drp240 | $900.00 | above range | $6.93 | median per-unit price of comparable items |
| Food | 22985168 Augason Farms Emergency All-in-one, 30-d | $881.02 | above range | $11.04 | comparable item: Augason Farms Emergency Food Gluten Free |
| Food | 200334932 Cheez-it 285pc Chz-it 4 Flav | $880.80 | above range | $8.64 | median price of the same kind of item |
| Food | 781138222 24 PCS RING POP LOLLIPOP, Case of 24 | $880.80 | above range | $8.60 | median price of the same kind of item |
| Food | 797325821 General Mills 220pcbugles/chex Mix | $871.20 | above range | $23.75 | comparable item: Chex Mix Muddy Buddies, 4.5 Oz., 7 Count |
| Food | 752249901 Mccormick 864pcmc Turkey Grav | $864.00 | above range | $7.92 | median price of its category |
| Food | 284784386 General Mills 216pcgm Fs Monsters | $859.68 | above range | $8.72 | median price of its category |
| Food | 39971042 Gummy Zone Sour Neon Wacky Worms, 1kg/2.2lbs, Bag, {Imported from Cana | $840.00 | above range | $19.70 | median per-unit price of comparable items |
| Food | 920354594 16 PC TRIPLE POWER PUSH POPS, Case of 12 | $828.15 | above range | $52.60 | median per-unit price of comparable items |
| Food | 678766387 36 PCS GIANT CHEWY SWEETARTS, Case of 10 | $824.25 | above range | $85.79 | median per-unit price of comparable items |
| Food | 795682625 (6 Pack) Cannone Borettane Onions In Balsamic Vin (6 pack) | $821.82 | above range | $7.92 | median price of its category |
| Food | 26958403 Wise Foods 720 Serving Package of Long Term Emergency Food Supply Free | $798.94 | above range | $8.72 | median price of its category |
| Food | 160311211 Gatorade 100pcga Var Display | $798.00 | above range | $1.85 | median per-unit price of comparable items |
| Food | 5102045732 PEPPERIDGE FARM COOKIES VARIETY | $778.40 | above range | $9.99 | comparable item: Grandma's Cookies Variety Pack, 30 Count |
| Food | 181503635 24 PCS PUSH POP CANDY, Case of 12 | $775.50 | above range | $49.33 | comparable item: 100 PCS COMIC PACK CANDY STICK, Case of 6 |
| Food | 444103472 Doritos 300pc Mixed Sept Nfl | $774.00 | above range | $6.59 | median price of the same kind of item |
| Food | 779628854 Jiffy Corn Muffin Mix, 8.5 oz | $771.12 | above range | $3.55 | median per-unit price of comparable items |
| Food | 536846989 ZEVIA TEA BLACK PEACH ORGANIC 12 FL OZ | $769.00 | above range | $5.94 | comparable item: Nixie Sparkling Water Peach Black Tea , 12 Fl Oz |
| Food | 289810564 (4 pack) (4 Pack) Yogi Teas Tea Bst Seller 3Flvr Dsp 48Pc 1 DS (Pack o | $768.00 | above range | $53.51 | median per-unit price of comparable items |
| Food | 380461265 General Mills 192pc Chexmix/gardet | $760.32 | above range | $114.62 | median per-unit price of comparable items |
| Food | 662581002 24 PCS RING POP TWIST, Case of 24 | $752.10 | above range | $15.64 | median price of the same kind of item |
| Food | 455904937 Easy Bake 66pcezb Whoopie | $748.02 | above range | $8.72 | median price of its category |
| Food | 5201416053 Missing Key Attributes : This title does not include any key attribute | $745.50 | above range | $14.42 | median price of its category |
| Food | 210816110 18 PCS BABY BOTTLE POP, Case of 16 | $724.80 | above range | $95.82 | median per-unit price of comparable items |
| Food | 55292814 Augason Farms Deluxe 4-Month 1-Person 10-Pail Kit Emergency Food Suppl | $724.56 | above range | $139.99 | comparable item: Augason Farms 2-Week 1-Person Emergency Food Suppl |
| Food | 19912563533 300 pc FL D82 RWB 1/2 DRP | $720.00 | above range | $201.24 | median per-unit price of comparable items |
| Food | 19934551441 18 pc SHPR WAW Browns | $720.00 | above range | $6.25 | median per-unit price of comparable items |
| Food | 16316069723 Cheetos Wednesday 1/2 DRP | $714.00 | above range | $7.86 | median price of the same kind of item |
| Food | 17195167827 240 pc WM GMI HNC MS LSMU | $712.80 | above range | $144.91 | median per-unit price of comparable items |
| Food | 284495468 (144 pack) (12 Pack) Sheila G'S Organic Chocolate Chip Brownie Brittle | $711.86 | above range | $9.93 | median price of the same kind of item |
| Food | 16545310397 480 Jarritos Pineapple and Mandarin 1.5L | $710.40 | above range | $5.41 | median per-unit price of comparable items |
| Food | 786470286 Hershey 479pcmilk Duds Tb | $708.92 | above range | $9.00 | median price of its category |
| Food | 177115343 Clear American Ca Blkch-pch-kl-mndo | $705.60 | above range | $0.99 | median per-unit price of comparable items |
| Food | 418001077 Clear American Ca Blkch-pch-strw-mn | $705.60 | above range | $0.99 | median per-unit price of comparable items |
| Food | 585983374 Clear American Ca Blkch-pch-strw-pc | $705.60 | above range | $13.94 | median price of its category |
| Food | 404537670 Rice Krispies Treats Rkt Original 40ct | $702.72 | above range | $56.37 | median per-unit price of comparable items |
| Food | 19916618639 348 pc 348 PC NERDS SWT SMM | $702.48 | above range | $13.11 | median price of the same kind of item |
| Food | 55292807 Augason Farms 6-Month 1-Person Emergency Food Supply | Shelter-in-Plac | $698.99 | above range | $8.72 | median price of its category |
| Food | 320277623 Doritos 300pc Mixed Nov | $696.00 | above range | $6.59 | median price of the same kind of item |
| Food | 997633983 J&D Manufacturing- SW2341 Energy Free Livestock Waterers, 22 Gallon, 2 | $692.13 | above range | $16.66 | median price of the same kind of item |
| Food | 16449108936 SHPR WVQ Virginia Tech | $672.00 | above range | $8.48 | median price of its category |
| Food | 911967463 Pepperidge Farm 84pcgld Fsh Blk Chd | $670.32 | above range | $9.00 | median price of its category |
| Food | 393759429 Kathy Kaye Popcorn Ball Half | $670.08 | above range | $17.95 | comparable item: Popcorn Ball |
| Food | 262337372 Kellogg 168pcdisney 3 Flavo | $661.92 | above range | $9.16 | median price of its category |
| Food | 584268338 Deer Park Spring Water, 25 fl oz, Single Aluminum Bottle | $643.68 | above range | $6.31 | comparable item: Deer Park Spring Water, 20 Fl Oz, Single Plastic B |
| Food | 573451302 PEPPERIDGE FARM STUFFING HERB | $643.20 | above range | $4.44 | median price of the same kind of item |
| Food | 20889470086 (5 pack) Gold Peak Zero Sugar Raspberry Iced Tea Bottle, 18.5 fl oz | $625.00 | above range | $27.26 | comparable item: (4 pack) (24 Bottles) Gold Peak Iced Tea, Raspberr |
| Food | 17449350377 252 pc WM PRO PM(4) SOUP RSHP | $624.96 | above range | $9.84 | median price of the same kind of item |
| Food | 471557731 Gatorade 528pcg Zero Vrty Di | $623.04 | above range | $11.10 | median price of the same kind of item |
| Food | 17823561312 126 pc WM GMI(4) LC/HNC/RPPB/CTC FS HPMU | $621.18 | above range | $76.08 | median per-unit price of comparable items |
| Food | 935472208 24 PCS CHEWY SWEETARTS, Case of 12 | $617.55 | above range | $43.08 | median per-unit price of comparable items |
| Food | 591621172 Nielsen-Massey Tahitian Pure Vanilla Extract, 128 oz | $615.86 | above range | $17.98 | median price of the same kind of item |
| Food | 17809713702 (30 pack) Hot Ones Mini Dab Hot Sauce Trio Gift Box, Includes Buffalo, | $599.40 | above range | $19.98 | comparable item: Hot Ones Mini Dab Hot Sauce Trio Gift Box, Include |
| Food | 699011469 SNYDERS OF HANOVER PRETZELS VARIETY | $596.16 | above range | $8.67 | comparable item: Snyder's of Hanover Variety Pack Pretzels, 20 Coun |
| Food | 488003500 (12 pack) (12 Pack) Love Good Fats Keto Friendly Peanut Butter Chocola | $592.65 | above range | $68.40 | comparable item: (12 pack) (12 Pack) Love Good Fats Keto Friendly P |
| Food | 820291080 (9 pack) (9 Pack) Eatingevolved Dark Chocolate Caramel Sea Salt Coconu | $592.65 | above range | $23.67 | comparable item: Eatingevolved Dark Chocolate Caramel Sea Salt Coco |
| Food | 205523835 Member's Mark Vegetable Oil (3 Quart, 2 Count) | $592.41 | above range | $19.85 | comparable item: Michigan Valley Brand Vegetable Oil, 128.0 FL OZ |
| Food | 501071723 24 PCS RING POP LOLLIPOP, Case of 12 | $588.30 | above range | $78.90 | median per-unit price of comparable items |
| Food | 37181922 Generic Mushroom Dried Porcini Xf, 16 Oz (pack O | $587.23 | above range | $9.28 | comparable item: Mushroom Dried Porcini Ba, 1 Lb (pack Of |
| Food | 1710867952 Betr Remedies Betr Sidekick 57pc | $585.79 | above range | $147.20 | comparable item: 136 pc HWN King 136ct Sidekick |
| Food | 860341880 2340 PCS DUM DUM POPS BULK, Case of 3 | $585.38 | above range | $9.00 | median price of its category |
| Food | 173175090 Daily Chef 4% Milkfat Minimum Small Curd Regular Cottage Cheese 5 lb T | $578.28 | above range | $8.74 | comparable item: Great Value 4% Milkfat Minimum Small Curd Cottage  |
| Food | 154408900 (3 pack) (3 Boxes) Yogi Teas Tea Bst Seller 3Flvr Dsp 48Pc 1 DS (Pack  | $576.00 | above range | $40.13 | median per-unit price of comparable items |
| Food | 930233912 Expert Grill 117pceg Flavor Mix | $570.96 | above range | $53.47 | median per-unit price of comparable items |
| Food | 38453377 Hot Fudge/Caramel Warmer with 1 Ladle & 1 Stainless Steel Pump | $570.00 | above range | $8.06 | median price of the same kind of item |
| Food | 225451441 Mac N Cheetos 448pcmnc Half Palle | $555.52 | above range | $8.72 | median price of its category |
| Food | 2015824349 (12 pack) McCormick Pure Vanilla Extract, 16.0 fl oz Bottle | $553.32 | above range | $17.98 | median price of the same kind of item |
| Food | 5129617690 PEPPERIDGE FARM GOLDFISH CRACKERS VARIETY | $552.64 | above range | $5.98 | comparable item: PEPPERIDGE FARM CRACKERS VARIETY |
| Food | 10756115 Weber Smokey Mountain Cooker Charcoal Smoker with 22-Inch | $549.00 | above range | $14.54 | median price of the same kind of item |
| Food | 15259868572 KFFKFF Synthetic Blooms | $544.99 | above range | $14.42 | median price of its category |
| Food | 170340588 Lucky Charms 136pcgmi(2) Lc Mmo | $541.28 | above range | $5.00 | comparable item: Lucky Charms Gm Lc 20.5oz 2pack |
| Food | 627661914 General Mills 420pcctc/hnc/lc Pou | $537.60 | above range | $5.00 | comparable item: General Mills Gm Ms 3pk Hnc-lc-hnc 36oz |
| Food | 15548011362 (10 pack) Wonderful Pistachios, No Shells Roasted & Salted Nuts, 12 Ou | $537.30 | above range | $119.40 | comparable item: Wonderful Pistachios No Shells Roasted & Salted Nu |
| Food | 37946746 American Specialties Surface Mounted Hand Dryer, White Enamel, 10.75X1 | $533.26 | above range | $8.72 | median price of its category |
| Food | 100975425 Sparkling Ice Tea Peach Tea 17 Fl Oz (Case of 12) | $530.90 | above range | $9.77 | comparable item: Sparkling Ice Tea Lemon Tea, 17 Fl Oz (Case of 12) |
| Food | 115162593 20PK LTO5 WORM CUSTOM LABELED | $528.76 | above range | $9.00 | median price of its category |
| Food | 989238460 Nielsen-Massey Mexican Pure Vanilla Extract, 128 oz | $527.87 | above range | $17.98 | median price of the same kind of item |
| Food | 588014535 Nielsen-Massey Pure Vanilla Extract 128 fl oz Bottle for Baking and Co | $517.12 | above range | $17.98 | median price of the same kind of item |
| Food | 13798756330 PEPPERIDGE FARM GOLDFISH CRACKERS VARIETY | $510.40 | above range | $5.98 | comparable item: PEPPERIDGE FARM CRACKERS VARIETY |
| Food | 8725323502 Lucano Amaro Zero Non-Alcoholic Italian Dealcoholized Aperitif Elixir  | $510.30 | above range | $277.68 | comparable item: Lucano Amaro Zero Non-Alcoholic Italian Dealcoholi |
| Food | 480628296 Nielsen-Massey Organic Fairtrade Madagascar Bourbon Pure Vanilla Extra | $509.95 | above range | $17.98 | median price of the same kind of item |
| Food | 389589685 Tortrix Creole Sauce Chips 6.3oz - Salsa Criolla (Pack of 8) | $505.37 | above range | $30.61 | comparable item: Tortrix Tacos Creole Sauce 6.34 oz - Salsa Criolla |
| Food | 36761043 Syrup Maple Pure Grade A, 1 Ga (pack Of | $501.01 | above range | $14.66 | median price of the same kind of item |
| Food | 481437356 24 PCS RING POP TWIST, Case of 12 | $500.55 | above range | $78.90 | median per-unit price of comparable items |
| Food | 101913072 Manhattan Chocolates Chocolate Leather - Dark Chocolate - Case Of 36 - | $0.48 | far below comparable items | $35.28 | comparable item: Manhattan Chocolates Chocolate Leather - Dark Choc |
| Food | 15673631 MAMA Noodles Pad Thai Instant Spicy Noodles w/ Delicious Thai Flavors, | $0.43 | far below comparable items | $16.58 | median per-unit price of comparable items |
| Food | 115047780 Blow Pop Lollipop, Assorted Berry, 100 Count | $0.24 | far below comparable items | $23.95 | comparable item: Charms Blow Pop, Assorted, 100-Count Pops |
| Food | 125268073 Tootsie Pops Assorted Flavor Lollipops, 0.6 Oz., 100 Count | $0.12 | far below comparable items | $11.42 | comparable item: Dum Dum Pops Assorted Flavor Lollipops, 10.4 oz.,  |
| Food | 119703102 (288 Count) International Delight Cold Stone Sweet Cream Creamer | $0.07 | below range | $41.27 | comparable item: (6 pack) International Delight Cold Stone Sweet Cr |
| Food | 829007865 (288 Count) International Delight Cinnabon Creamer | $0.07 | below range | $24.60 | comparable item: (4 pack) International Delight Hazelnut Creamer, 4 |
| Food | 130204721 (288 Count) International Delight Hershey Chocolate caramel Creamer | $0.06 | below range | $76.20 | comparable item: International Delight HERSHEY’S Chocolate Caramel  |
| Food | 135282277 (288 Count) International Delight Irish Cream Creamer | $0.06 | below range | $13.94 | median price of its category |
| Food | 510494953 General N Joy Sugar Packet | $0.03 | below range | $27.12 | comparable item: Genuine Joe Sugar Packets - Packet - 0.099 Oz (2.8 |
| Food | 551782729 Diamond Crystal Hometown Market Asprtmame Blue Sweetener | $0.03 | below range | $11.94 | median price of the same kind of item |
| Food | 910247393 Diamond Crystal Hometown Market Sugar Sub Pink Sweetener | $0.03 | below range | $11.94 | median price of the same kind of item |
| Food | 207777616 POP without AV | $0.02 | below range | $15.64 | median price of the same kind of item |
| Food | 36282224 Jack Link's Wild Side Teriyaki Sausage, 4 ct, 12 oz | $0.01 | below range | $13.32 | median per-unit price of comparable items |
| Food | 100140315 Fresh Cravings Chunky Mild Salsa 2oz | $0.01 | below range | $7.30 | median price of the same kind of item |
| Food | 114241839 DiLuigi Foods Beef Steak Kabobs with Peppers Onions | $0.01 | below range | $6.14 | median price of the same kind of item |
| Food | 139078114 SIMPSON FARMS Ground Beef 85% Lean/ 15% Fat | $0.01 | below range | $10.88 | comparable item: Jensen Ground Beef and Pork Blend Frozen Patties,  |
| Food | 143982970 DiLuigi Chicken Breast Kabobs | $0.01 | below range | $10.20 | comparable item: HORMEL BREAST OF CHICKEN 2/10oz |
| Food | 155698379 Wise Organic & Kosher Free-Range Chicken Drumsticks, 1.0 PACKAGE | $0.01 | below range | $12.24 | comparable item: (3 pack) (3 Pack) Swanson Organic Free-Range Chick |
| Food | 158699169 Wise Organic & Kosher Free-Range Chicken Wings, 1.0 PACKAGE | $0.01 | below range | $6.83 | median price of its category |
| Food | 165824816 Kunzler All Natural Uncured Black Forest Ham | $0.01 | below range | $4.98 | comparable item: Prima Della Black Forest Ham |
| Food | 173972297 Fresh Cravings Pico De Gallo Mild Salsa 2oz | $0.01 | below range | $7.30 | median price of the same kind of item |
| Food | 182977430 The Piggery Pork Chips Dry Rubbed W/ Rosemany + Thyme, 2.0 CT | $0.01 | below range | $9.30 | median price of the same kind of item |
| Food | 192945244 Wise Organic & Kosher Whole Chicken, 1.0 CT | $0.01 | below range | $6.83 | median price of its category |
| Food | 196459912 Shady Brook Farms Young Turkey Breast, 1.0 CT | $0.01 | below range | $6.44 | median price of the same kind of item |
| Food | 201352560 Lunds & Byerlys Uncured Honey Ham 1 ea | $0.01 | below range | $39.00 | comparable item: Hickory Farms Honey Ham, 4 - 5 lbs |
| Food | 214944319 Brunckhorst Boars Head Cheese, 1 ea | $0.01 | below range | $5.26 | median price of the same kind of item |
| Food | 268276998 Prairie Fresh Pork Loin Backribs 1 ea | $0.01 | below range | $6.56 | comparable item: Prairie Fresh Prime Cracked Rosemary Pork Loin Fil |
| Food | 288411977 Instant K Cafe Solo Display | $0.01 | below range | $8.72 | median price of its category |
| Food | 308970211 Pride of the Farm Drumsticks Turkey 1 ea | $0.01 | below range | $2.73 | comparable item: Chef-Ko Smoked Turkey Drumsticks |
| Food | 351061195 Purely Inspired Customer Value Program For 12 Inch Bikes | $0.01 | below range | $23.57 | median price of the same kind of item |
| Food | 357582687 Clemens Food Group Hatfield Pork Tenderloin, 1 ea | $0.01 | below range | $6.83 | median price of its category |
| Food | 399053009 Coborn's Boneless Americas Cut Chop Premium Duroc Pork 1 ea | $0.01 | below range | $6.51 | median price of the same kind of item |
| Food | 428702933 Winchester Farms Ground Beef Stuffed Peppers 1 Each | $0.01 | below range | $6.83 | median price of its category |
| Food | 429767900 Services Non Taxable Cvmp | $0.01 | below range | $7.92 | median price of its category |
| Food | 441721276 Lunds & Byerlys Tinga Chicken Empanada 1 ea | $0.01 | below range | $9.16 | median price of its category |
| Food | 514084495 Hormel Always Tender Combo Pork Rib Chops 1 ea Tray | $0.01 | below range | $6.51 | median price of the same kind of item |
| Food | 555920767 Meijer Markets of Meijer Chicken Breast, 1 ea | $0.01 | below range | $6.83 | median price of its category |
| Food | 620674899 Bella Linea Coffee Red Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Food | 635961391 MTN DEW AMP GAME FUEL, 4 Flavor Variety Pack, 16 oz Cans, 12 Count + F | $0.01 | below range | $55.55 | median per-unit price of comparable items |
| Food | 653271293 Pride of the Farm Wings Turkey 1 ea | $0.01 | below range | $6.44 | median price of the same kind of item |
| Food | 661485947 Sugardale Center Slice Smoked Ham 1 ea | $0.01 | below range | $7.28 | median price of the same kind of item |
| Food | 684792813 Hormel Always Tender Hatch Seasoned Pork Rib Chop 1 ea | $0.01 | below range | $6.51 | median price of the same kind of item |
| Food | 687783849 Mitica Marcona Almonds With Skins | $0.01 | below range | $7.38 | comparable item: Nature's Tree Marcona Almonds, 8.5 oz Bag |
| Food | 731096895 N'Joy Saccharin Sugar Substitute, 83024 (21202066) | $0.01 | below range | $51.94 | median per-unit price of comparable items |
| Food | 735833430 DCK 2021 WM CFT 52FT. CDT POP KIT | $0.01 | below range | $15.64 | median price of the same kind of item |
| Food | 759357673 Freshness Guaranteed Chocolate Chip Cookie Topped Donuts, 10 oz, 4 Cou | $0.01 | below range | $21.07 | comparable item: Freshness Guaranteed Chocolate Chip Muffin Minis,  |
| Food | 771705201 Smithfield Smithfield Smokehouse Reserve Ham, 1 ea | $0.01 | below range | $7.28 | median price of the same kind of item |
| Food | 818070456 Boar's Head Vermont Cheddar Cheese | $0.01 | below range | $5.43 | comparable item: Fritz Cheddar Cheese, 16 oz |
| Food | 869515102 Pride of the Farm Thighs Turkey 1 ea | $0.01 | below range | $6.44 | median price of the same kind of item |
| Food | 913604428 Red Smith Pigs Feet | $0.01 | below range | $9.00 | median price of its category |
| Food | 921416426 Lunds & Byerlys Smoked Uncured Ham 1 ea | $0.01 | below range | $9.97 | comparable item: Dietz And Watson D&w Ham Applewood Smoked Uncured  |
| Food | 978507180 Mr Coffee Cafe Barrista Display | $0.01 | below range | $9.44 | median price of the same kind of item |
| Health and Medicine | 984866819 BinaxNOW COVID?19 Antigen Self Test (2 Count) 864 Pack | $13,720.32 | above range | $15.88 | comparable item: BinaxNOW COVID?19 Antigen Self Test (2 Count) 120  |
| Health and Medicine | 28645756 NatureWorks® Swedish Bitters Traditional European Herbal Extract Used  | $11,634.55 | above range | $134.27 | median per-unit price of comparable items |
| Health and Medicine | 14654136 Nature's Way Vitamin D3 1000 IU, Fast Absorbing, 16 Ounces, Natural Be | $10,987.91 | above range | $36.38 | median per-unit price of comparable items |
| Health and Medicine | 174508250 (300 pack) (300 pack) Omron 3 Series Upper Arm Blood Pressure Monitor  | $10,356.00 | above range | $50.00 | comparable item: Omron 5 Series Upper Arm Blood Pressure Monitor (M |
| Health and Medicine | 302806384 Kurodo - Executive Level Commercial 4D Deep Tissue Zero Gravity Massag | $10,344.82 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 189371136 Primal Gold 14 Karat Yellow Gold Figaro Link ID Bracelet | $10,060.92 | above range | $224.24 | comparable item: Primal Gold 14 Karat Yellow Gold Semi-Solid Figaro |
| Health and Medicine | 674162318 Sambucus Zinc Lozenges with Elderberry and Vitamin C, 24 Lozenges, Pep | $9,999.00 | above range | $13.09 | comparable item: Nature's Way Sambucus Immune Elderberry Lozenges w |
| Health and Medicine | 36978743 Intelect SWD100 shortwave diathermy | $9,848.65 | above range | $200.08 | comparable item: Intelect Shortwave Diathermy - electrode arm (righ |
| Health and Medicine | 664515311 JP1100 - Deluxe 4D Massage Chair | Zero Gravity Recline | Air Compress | $9,000.00 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 738175559 JP1100 - Deluxe 4D Massage Chair | Zero Gravity Recline | Air Compress | $9,000.00 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 827219990 JP1100 - Deluxe 4D Massage Chair | Zero Gravity Recline | Air Compress | $9,000.00 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 295273437 Spring Valley 749pcbts Vitamin Fp | $6,855.92 | above range | $16.43 | median price of the same kind of item |
| Health and Medicine | 201989844 Spring Valley 733pcbts Vitamin Fp | $6,697.84 | above range | $16.43 | median price of the same kind of item |
| Health and Medicine | 365620183 Spring Valley 749pcbts Vitamin Fp | $6,665.52 | above range | $8.16 | comparable item: Spring Valley Vitamin D |
| Health and Medicine | 31491595 14k Yellow Gold Solid Polished Figaro ID Bracelet 8 Inch 8mm Box Clasp | $6,579.72 | above range | $1,860.80 | comparable item: 14k Yellow Gold Solid Polished Curb ID Bracelet 8  |
| Health and Medicine | 550353794 Spring Valley 733pcbts Vit Fp Cm | $6,312.28 | above range | $19.66 | median price of its category |
| Health and Medicine | 164859911 14k Yellow Gold Solid Polished Figaro ID Bracelet 8 Inch 9mm Box Clasp | $5,891.28 | above range | $1,860.80 | comparable item: 14k Yellow Gold Solid Polished Curb ID Bracelet 8  |
| Health and Medicine | 31478806 14k Yellow Gold Solid Hand Polished Traditional Link ID Bracelet 12mm  | $5,889.44 | above range | $1,860.80 | comparable item: 14k Yellow Gold Solid Polished Curb ID Bracelet 8  |
| Health and Medicine | 149316891 OSAKI JAPAN PREMIUM 4D | $5,600.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 304144600 OSAKI JAPAN PREMIUM 4D | $5,600.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 124426530 16 FT Sofia & Scoop VERC | $5,533.84 | above range | $18.55 | median price of its category |
| Health and Medicine | 439958254 Weller Filtration T0053661299N ZERO SMOG 4V 100/120V B WITH GAS FILTER | $5,465.26 | above range | $39.99 | median price of its category |
| Health and Medicine | 50668318 Body-Solid - G9B Commercial Gym - 2 Weight Stack Gym | $5,345.00 | above range | $16.42 | median price of the same kind of item |
| Health and Medicine | 54446712 Drive Medical King Cobra Executive Power Scooter, 4 Wheel, 22" Captain | $5,249.00 | above range | $155.66 | median price of the same kind of item |
| Health and Medicine | 968593459 Kagra - Premium 4D Heated Zero Gravity Massage Chair | Dual Layer Body | $4,999.99 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 43224560 Drive Medical Maverick Executive Three Wheel Power Scooter | $4,799.00 | above range | $768.00 | comparable item: Drive Medical ZooMe Three Wheel Recreational Power |
| Health and Medicine | 356696751 OSAKI JAPAN PREMIUM 4D | $4,516.13 | above range | $19.66 | median price of its category |
| Health and Medicine | 10924452 Panasonic Real Pro Ultra Intensity with Arm Massage Chair in Brown | $4,499.95 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 43224559 Drive Medical Maverick Executive Three Wheel Power Scooter | $4,483.85 | above range | $768.00 | comparable item: Drive Medical ZooMe Three Wheel Recreational Power |
| Health and Medicine | 460207530 LV00569 - Massage Chair, Chocolate PU - Pacari | $4,055.68 | above range | $42.99 | median price of the same kind of item |
| Health and Medicine | 376447613 Foster Grant 398pc-menscaliblue | $3,968.06 | above range | $10.00 | comparable item: Foster Grant Bnf |
| Health and Medicine | 21864725 Drive Medical Osprey Heavy Duty Mobility | $3,899.00 | above range | $275.33 | median price of its category |
| Health and Medicine | 706695535 Intelect Legend XT - 4-channel Stim / Ultrasound combo system | $3,748.75 | above range | $19.66 | median price of its category |
| Health and Medicine | 559602485 ZooMe-R 4-Wheel Recreational Power Scooter | $3,643.75 | above range | $768.00 | comparable item: Drive Medical ZooMe Three Wheel Recreational Power |
| Health and Medicine | 181260470 Plant Therapy Blue Tansy Organic Essential Oil 1 KG 100% Pure | $3,553.85 | above range | $13.78 | median price of the same kind of item |
| Health and Medicine | 218930538 Seeboost Right Large (54-16-140) | $3,500.00 | above range | $10.16 | comparable item: 7" elastic wrist supports right, x-large 8.5-10" |
| Health and Medicine | 231704800 Seeboost Right Small (51-16-140) | $3,500.00 | above range | $18.55 | median price of its category |
| Health and Medicine | 604826255 Seeboost Right Long (53-16-145) | $3,500.00 | above range | $49.00 | comparable item: The Backnobber, long |
| Health and Medicine | 789726996 Seeboost Left Small (51-16-140) | $3,500.00 | above range | $18.55 | median price of its category |
| Health and Medicine | 804205995 Seeboost Left Long (53-16-145) | $3,500.00 | above range | $49.00 | comparable item: The Backnobber, long |
| Health and Medicine | 155046774 Body-Solid - GS348BP4 Smith Machine Package | $3,466.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 435198812 Jin 2.0 - Deluxe Heated SL Track Zero Gravity Massage Chair | Full Bod | $3,400.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 509585801 Jin 2.0 - Deluxe Heated SL Track Zero Gravity Massage Chair | Full Bod | $3,400.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 50686113 Body Solid - G6B Bi-Angular Home Gym | $3,365.00 | above range | $1,710.00 | comparable item: Body Solid - G1B Compact Home Gym |
| Health and Medicine | 50676095 Body Solid - G5S Single Stack Home Gym | $3,360.00 | above range | $1,710.00 | comparable item: Body Solid - G1B Compact Home Gym |
| Health and Medicine | 267596667 (100 pack) DisposeRx Single-Use Drug Disposal Packets, 3,000 Ct (100 P | $3,330.00 | above range | $646.00 | comparable item: DisposeRx Single-Use Drug Disposal Packets, 600 Ct |
| Health and Medicine | 40808629 Health o meter Professional 2600KL Wheelchair Scale | $3,295.83 | above range | $210.07 | median price of the same kind of item |
| Health and Medicine | 31502629 14k Yellow Gold Solid Polished Fold-over 7mm Nugget ID Bracelet 7 Inch | $3,210.76 | above range | $1,860.80 | comparable item: 14k Yellow Gold Solid Polished Curb ID Bracelet 8  |
| Health and Medicine | 185875634 Elkay WCLWO1923OSDC Elkay Sturdibilt Stainless Steel 19" x 23" x 4", W | $3,149.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 520939039 Drive Medical Panther 4-Wheel Heavy Duty Scooter, 20" Captain Seat | $3,149.00 | above range | $1,249.00 | comparable item: Drive Medical Phoenix Heavy Duty Power Scooter, 3  |
| Health and Medicine | 915482276 Drive Medical Panther 4-Wheel Heavy Duty Scooter, 22" Captain Seat | $3,149.00 | above range | $1,249.00 | comparable item: Drive Medical Phoenix Heavy Duty Power Scooter, 3  |
| Health and Medicine | 22656293 Hydrocollator heating unit, M-4 w/8 os, 8 neck | $3,118.95 | above range | $1,625.00 | comparable item: Hydrocollator mobile heating unit - SS-2 w/2 std,  |
| Health and Medicine | 35214193 Hydrocollator heating unit, M-4 (24 standard packs) | $3,118.95 | above range | $1,834.68 | comparable item: Hydrocollator heating unit, M-2 (12 standard packs |
| Health and Medicine | 29137984 SSN 811302 Cable Crossover Machine | $3,033.31 | above range | $19.66 | median price of its category |
| Health and Medicine | 14829934 Tanita TBF-300WA Wrestling Body Composition Analyzer and Bath Scale | $2,999.99 | above range | $1,299.99 | comparable item: BF-350 Body Composition Analyzer and Bath Scale |
| Health and Medicine | 17748375 Pride Pursuit 4-Wheel Personal Mobility Vehicle, Red | $2,999.00 | above range | $275.33 | median price of its category |
| Health and Medicine | 253712307 ALFI brand HammockTub1-BM Black Matte 79" Acrylic Suspended Wall Mount | $2,999.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 14251927 Drive Medical Stand Assist Lift | $2,943.55 | above range | $109.20 | comparable item: Drive Medical LiftWalker with Retractable Stand As |
| Health and Medicine | 972640741 Primal Gold 14 Karat Yellow Gold Medical Soft Diamond Shape Red Enamel | $2,921.06 | above range | $340.38 | comparable item: Primal Gold 14 Karat Yellow Gold Medical Soft Diam |
| Health and Medicine | 295474049 Bob Dale 99-1-9751-10 NinjaÂ® Star 5 DyneemaÂÂ® Gauntlet Full Crinkle  | $2,916.00 | above range | $1,834.56 | comparable item: Bob Dale 99-1-9750-8 Ninja® Star 3 Dyneema® Gauntl |
| Health and Medicine | 183591061 Primal Gold 14 Karat Yellow Gold Medical Soft Diamond Shape Red Enamel | $2,858.32 | above range | $340.38 | comparable item: Primal Gold 14 Karat Yellow Gold Medical Soft Diam |
| Health and Medicine | 17748377 Pride Pursuit 4-Wheel Personal Mobility Vehicle, Blue | $2,854.84 | above range | $275.33 | median price of its category |
| Health and Medicine | 604396341 Primal Gold 14 Karat Yellow Gold Medical Red Enamel Curb ID Bracelet | $2,854.76 | above range | $1,188.38 | comparable item: Primal Gold 14 Karat Yellow Gold Medical Red Ename |
| Health and Medicine | 502240645 Top End Excelerator Stock Handcycle, 20" Seat Width, Red, TE10006-V3 | $2,825.33 | above range | $19.66 | median price of its category |
| Health and Medicine | 123745486 Drive Medical ZooMe Auto-Flex Folding Travel Scooter, Blue | $2,824.00 | above range | $155.66 | median price of the same kind of item |
| Health and Medicine | 910856659 Primal Gold 14 Karat Yellow Gold Medical Soft Diamond Shape Red Enamel | $2,809.18 | above range | $1,159.95 | comparable item: Primal Gold 14 Karat Yellow Gold Medical Soft Diam |
| Health and Medicine | 40808325 Health o meter Professional 2500KL Wheelchair Scale with Bluetooth | $2,797.00 | above range | $210.07 | median price of the same kind of item |
| Health and Medicine | 841900651 5' x 5' Floor Scale 5000 lb x 1 lb Weight Capacity NTEP Certified Wire | $2,779.30 | above range | $16.42 | median price of the same kind of item |
| Health and Medicine | 19270232 Drive Medical Med Aire Plus Bariatric Heavy Duty Low Air Loss Mattress | $2,774.00 | above range | $188.15 | median price of the same kind of item |
| Health and Medicine | 794828792 Nonin Avant 2120 pulse oximeter with blood pressure cuff | $2,750.00 | above range | $29.99 | median price of the same kind of item |
| Health and Medicine | 809515155 Plant Therapy Blue Tansy Essential Oil | 100% Pure, Undiluted, Natural | $2,703.46 | above range | $29.95 | comparable item: Plant Therapy Lavender Set Made From 100% Pure, Un |
| Health and Medicine | 347191806 (12 pack) MaxxHaul 70275 Aluminum Cargo Carrier with 60" Ramp | $2,681.16 | above range | $96.83 | comparable item: Speedway 500lbs Aluminum Cargo Carrier |
| Health and Medicine | 34203359 Drive Medical True Low Air Loss Mattress System with Pulsation, 10" | $2,641.76 | above range | $1,290.00 | comparable item: Drive Medical Med Aire Plus Low Air Loss Mattress  |
| Health and Medicine | 256441977 Top End Preliminator Stock Junior Varsity Racing Wheelchair, 14" Seat  | $2,626.00 | above range | $210.07 | median price of the same kind of item |
| Health and Medicine | 704366145 Top End Preliminator Stock Prep Racing Wheelchair, 12" Seat Width, Saf | $2,626.00 | above range | $210.07 | median price of the same kind of item |
| Health and Medicine | 375954322 Bob Dale 99-1-9751-11 Ninja® Star 5 Dyneema® Gauntlet Full Crinkle Lat | $2,624.40 | above range | $1,834.56 | comparable item: Bob Dale 99-1-9750-8 Ninja® Star 3 Dyneema® Gauntl |
| Health and Medicine | 19270265 Drive Medical Med Aire Plus Bariatric Low Air Loss Mattress Replacemen | $2,554.43 | above range | $1,019.88 | comparable item: Drive Medical Med Aire Plus Bariatric Low Air Loss |
| Health and Medicine | 161726663 Opticell Ag+ Gelling Fiber with Silver - MSC98812EP | $2,525.23 | above range | $164.48 | comparable item: Opticell Ag+ Gelling Fiber with Silver - MSC9845EP |
| Health and Medicine | 979826105 Primal Gold 14 Karat Yellow Gold Medical Red Enamel Flat Curb Link ID  | $2,519.95 | above range | $907.82 | comparable item: Primal Gold 14 Karat Yellow Gold Medical Red Ename |
| Health and Medicine | 10542823 Panasonic EP30003TU Real Pro Ultra Massage Lounger, Brown | $2,499.88 | above range | $19.66 | median price of its category |
| Health and Medicine | 40808513 Health O Meter Professional Wheelchair Scale | $2,497.00 | above range | $59.85 | comparable item: Perfect Scale |
| Health and Medicine | 17365186 Body Solid - SBL460P4 Leverage Gym Package | $2,495.00 | above range | $19.66 | median price of its category |
| Health and Medicine | 27081656 Drive Medical Blue Medalist Heavy Duty P | $2,492.00 | above range | $102.24 | comparable item: Heavy Duty 3-in-1 Commode |
| Health and Medicine | 724361779 Relief Pak Heating Unit, 24-Pack Capacity, Mobile with (8) Oversize an | $2,453.58 | above range | $13.16 | median price of the same kind of item |
| Health and Medicine | 23217992 Drive Medical Future Air True Low Air Mattress System | $2,440.00 | above range | $1,290.00 | comparable item: Drive Medical Med Aire Plus Low Air Loss Mattress  |
| Health and Medicine | 35214192 Hydrocollator 00-2502-3 Mobile Heating Unit M-4 W/6 Std 6 Os 6 Neck | $2,392.92 | above range | $1,834.68 | comparable item: Hydrocollator 00-2402-2 Mobile Heating Unit M-2 W/ |
| Health and Medicine | 20452515421 (2 pack) Jabra Enhance Select 50R Rechargeable, Behind-the-Ear Hearing | $2,390.00 | above range | $1,195.00 | comparable item: Jabra Enhance Select 50R Rechargeable, Behind-the- |
| Health and Medicine | 20465264140 (2 pack) Jabra Enhance Select 50R, Medical-Grade, Behind-the-Ear Heari | $2,390.00 | above range | $910.00 | comparable item: Jabra Enhance Select 50R, Medical-Grade, Behind-th |
| Health and Medicine | 535893829 (120 Pack) BinaxNOW COVID‐19 Antigen Self Test (2 Tests) | $2,385.60 | above range | $1,789.20 | comparable item: (98 pack) (98 pack) BinaxNOW COVID‐19 Antigen Self |
| Health and Medicine | 549548875 Relief Pak Heating Unit, 24-Pack Capacity, Mobile with (24) Standard P | $2,370.27 | above range | $13.16 | median price of the same kind of item |
| Health and Medicine | 474774307 Invacare Aquatec Ocean Ergo VIP Reclining Shower Wheelchair Rolling Ch | $2,345.00 | above range | $39.99 | comparable item: Aquatec Ocean Comfort Soft Backrest for Ergo VIP S |
| Health and Medicine | 17054656546 240 pc 240Pcs Vicks Health Wellness Wall | $2,312.80 | above range | $42.71 | median per-unit price of comparable items |
| Health and Medicine | 40808416 Healthometer 2650KL Wheelchair Scale-1000 lb/454 kg Capacity | $2,301.00 | above range | $114.99 | comparable item: Health O Meter LCD Floor Scale 397 lbs. / 180 kg C |
| Health and Medicine | 236927972 Relief Pak Heating Unit, 24-Pack Capacity, Mobile with (24) Standard P | $2,250.00 | above range | $13.16 | median price of the same kind of item |
| Health and Medicine | 27049736 Drive Medical Blue Renegade Power Wheelc | $2,238.60 | above range | $59.31 | comparable item: Drive Medical Power Mobility Rear Basket |
| Health and Medicine | 15337104856 Wondertech® 2-Piece Adjustable Wedge Set | $2,234.48 | above range | $31.49 | comparable item: Lisle 69620 Wedge Assortment Set 5 Piece |
| Health and Medicine | 906802635 Primal Gold 14 Karat Yellow Gold Medical Red Enamel Flat Curb Link ID  | $2,230.99 | above range | $907.82 | comparable item: Primal Gold 14 Karat Yellow Gold Medical Red Ename |
| Health and Medicine | 419566003 Osaki Pro Synergy Brown | $2,216.65 | above range | $1,999.00 | comparable item: Osaki Pro Synergy Taupe |
| Health and Medicine | 724654092 DisposeRx Single-Use Drug Disposal Packets, 2,000 Ct (20 packs of 100) | $2,200.00 | above range | $646.00 | comparable item: DisposeRx Single-Use Drug Disposal Packets, 600 Ct |
| Health and Medicine | 205637974 Bob Dale 99-1-9750-9 Ninja® Star 3 Dyneema® Gauntlet Full Crinkle Late | $2,184.00 | above range | $1,834.56 | comparable item: Bob Dale 99-1-9750-8 Ninja® Star 3 Dyneema® Gauntl |
| Health and Medicine | 796155676 Bob Dale 99-1-9750-7 Ninja® Star 3 Dyneema® Gauntlet Full Crinkle Late | $2,184.00 | above range | $1,834.56 | comparable item: Bob Dale 99-1-9750-8 Ninja® Star 3 Dyneema® Gauntl |
| Health and Medicine | 129468396 Equate Antibacterial Gauze Pads, 2 in x 2 in, 24 Count | $0.59 | far below comparable items | $1.73 | comparable item: (3 pack) Equate Antibacterial Gauze Pads, 2 in x 2 |
| Health and Medicine | 444003742 LIT™ On-The-Go Pre-Workout, Snow Cone, 16 Ounces | $0.40 | far below comparable items | $5.49 | comparable item: Beyond Raw® LIT™ On-The-Go Pre-Workout, Jolly Ranc |
| Health and Medicine | 525433284 Sundown Melatonin 10 Mg, 90 Capsules | $0.16 | far below comparable items | $7.17 | comparable item: Life Extension Melatonin 1 mg, 60 Capsules |
| Health and Medicine | 11162655308 Pip Lancets 30G | $0.09 | below range | $3.34 | comparable item: Relion 30g Lancets 200ct |
| Health and Medicine | 390451725 ibuprofen | $0.08 | below range | $6.23 | comparable item: IBUPROFEN |
| Health and Medicine | 15557056062 LORAZEPAM TB ANI 2MG | $0.08 | below range | $19.66 | median price of its category |
| Health and Medicine | 15670901637 GLYCERIN USP M 100ML | $0.08 | below range | $5.37 | comparable item: Pharmacy Glycerin Liqui 473ml |
| Health and Medicine | 15685659367 ORA-PLUS ORAL 473ML | $0.08 | below range | $126.96 | median per-unit price of comparable items |
| Health and Medicine | 295737828 ibuprofen | $0.06 | below range | $6.23 | comparable item: IBUPROFEN |
| Health and Medicine | 103451097 Major Banophen Diphenhydramine Hydrochloride, Pink, 100 ct | $0.05 | below range | $5.97 | comparable item: Major Banophen Diphenhydramine Hydrochloride Mini  |
| Health and Medicine | 343961824 Easy Touch 21G X 1" | $0.04 | below range | $19.88 | comparable item: Brother P-Touch |
| Health and Medicine | 140282905 Major ProSight Vitamin & Mineral Ascorbic Acid Supplement Tabs, Gray,  | $0.03 | below range | $6.13 | comparable item: Major Certa-Vite Ascorbic Acid Vitamin & Mineral S |
| Health and Medicine | 15523469498 DIAZEPAM TB AURO 2MG | $0.03 | below range | $19.66 | median price of its category |
| Health and Medicine | 15541463002 DIAZEPAM TB AURO 2MG | $0.03 | below range | $19.66 | median price of its category |
| Health and Medicine | 400460056 72 PC SUNGLASS RACK | $0.02 | below range | $6.52 | median per-unit price of comparable items |
| Health and Medicine | 6932716225 INFUSE® for Astigmatism | $0.02 | below range | $99.00 | comparable item: BAUSCH & LOMB INFUSE® |
| Health and Medicine | 10902524938 PRECISION 7 SPHERE TRIAL | $0.02 | below range | $19.66 | median price of its category |
| Health and Medicine | 13101116169 Clariti 1 D MF 3 Trial Add HI | $0.02 | below range | $19.66 | median price of its category |
| Health and Medicine | 19445268635 ACUVUE® OASYS MAX 1-Day Multifocal for Astigmatism | $0.02 | below range | $125.00 | comparable item: ULTRA® Multifocal for Astigmatism |
| Health and Medicine | 251424300 Bausch & Lomb +0.00 EUREKA! DAILY - 90 PACK | $0.01 | below range | $47.86 | comparable item: Bausch & Lomb +0.50 EUREKA! DAILY - 90 PACK |
| Health and Medicine | 564171878 WMD49 2021 Polar Optics Sunglass Header GRAPHIC | $0.01 | below range | $18.55 | median price of its category |
| Health and Medicine | 635487500 Equate Folding Knee Walker with Storage Bag Riser Sample | $0.01 | below range | $138.00 | comparable item: Equate Folding Knee Walker with Adjustable Height  |
| Health and Medicine | 939162041 WMD49 2021 Polar Optics Tower Sunglass Header GRAPHIC | $0.01 | below range | $18.55 | median price of its category |
| Health and Medicine | 9772668018 OMEPRAZOLE 20 MG | $0.01 | below range | $92.99 | comparable item: Equaline Omeprazole 20mg, 42 CT (Pack of 3) |
| Home | 5169079673 Hamilton Beach 1 cu ft Countertop Microwave Oven, Gray | $0.09 | below range | $55.89 | comparable item: Hamilton Beach 0.7 cu ft Countertop Microwave Oven |
| Home | 16352812095 Mainstays 38 Ounce Round Plastic Etched Holly Bowl, Green | $0.05 | below range | $0.50 | comparable item: Mainstays 38 Ounce Round Plastic Etched Tree Bowl, |
| Home | 135705331 Vendor Name Steamfast Traveliron Non-working Display | $0.04 | below range | $17.99 | median price of its category |
| Home | 165632493 Hamilton Beach Durathon Digital Display | $0.04 | below range | $30.00 | median price of its category |
| Home | 669412998 Chicago Cutlery Precision Cut Walnut Handle Block Knife Set, 14 Piece | $0.03 | below range | $52.47 | comparable item: Chicago Cutlery 14-Piece Walnut Knife Set |
| Home | 768982612 My Mini Noodle Cooker Display | $0.03 | below range | $14.00 | comparable item: MY KETO KITCHEN EGG COOKER |
| Home | 798723826 Chicago Cutlery Cc Precision Cut Intgrtd Ss 16pc Set Pp | $0.03 | below range | $14.68 | comparable item: Precision Cut 4pc Steakhouse Set |
| Home | 194766243 Hamilton Beach Hb Retrac Cord Iron Display | $0.03 | below range | $19.94 | comparable item: Hamilton Beach Retractable Cord Iron | Model# 1428 |
| Home | 213766919 Hamilton Beach Iron/steamer Display | $0.03 | below range | $21.91 | comparable item: Hamilton Beach Steam Iron 14672 |
| Home | 305322098 Cs6916-16 Vtech Display | $0.03 | below range | $30.00 | median price of its category |
| Home | 415788714 Hamilton Beach Retractable Cord Iron Dsp | $0.03 | below range | $19.94 | comparable item: Hamilton Beach Retractable Cord Iron | Model# 1428 |
| Home | 437416010 Chi Iron Retractable Cord Display | $0.03 | below range | $69.98 | comparable item: CHI Iron with Retractable Cord | Model# 13106 |
| Home | 823434967 Hamilton Beach Durathon Iron Display | $0.03 | below range | $60.53 | comparable item: Hamilton Beach Durathon Nonstick Soleplate Iron Mo |
| Home | 877709102 Hamilton Beach Hb Iron Display For Iron/steamer | $0.03 | below range | $30.00 | median price of its category |
| Home | 108533019 BLACK+DECKER Professional Steam Iron with Stainless Steel Soleplate an | $0.03 | below range | $49.99 | comparable item: BLACK+DECKER Allure™ Professional Steam Iron, Stai |
| Home | 142359748 Oster 1.3 Cubic Ft./1000 Watt Microwave | $0.03 | below range | $48.65 | median price of the same kind of item |
| Home | 202646193 Instant Pot 20 Cup Rice Disp | $0.03 | below range | $23.97 | comparable item: Continental Electric 10 Cup Rice Cooker |
| Home | 232991387 HOOVER SMARTWASH CARPET CLEANER DISPLAY DUFH52001G | $0.03 | below range | $19.90 | median price of the same kind of item |
| Home | 265249041 SHARK IZ340H STICK VAC DISPLAY | $0.03 | below range | $49.86 | comparable item: Shark Bagless Stick Vac |
| Home | 396358999 BLACK+DECKER™ One Step Steam Iron - SG Display | $0.03 | below range | $58.49 | comparable item: BLACK+DECKER One Step Steam Iron with Nonstick Sol |
| Home | 558230060 BLACK+DECKER Non-Stick Smart Steam Iron OPP - SG Display | $0.03 | below range | $29.23 | comparable item: Black+Decker Smart Steam Iron, 1100 Watts, Adjusta |
| Home | 925134126 Beautiful White Coffee Maker NON-WORKING DISPLAY | $0.03 | below range | $37.84 | median price of the same kind of item |
| Home | 966650042 BISSELL Little Green NWD | $0.03 | below range | $92.99 | comparable item: BISSELL Little Green 14007 Portable Vacuum Cleaner |
| Home | 1005868999 A10-D Plus NWD Dummy | $0.03 | below range | $67.60 | median price of the same kind of item |
| Home | 1597678711 Ninja Blast Cordless Blender Display, DSPBC100WMP | $0.03 | below range | $84.97 | comparable item: Ninja Blast Cordless Portable Blender, BC200PR |
| Home | 2586091480 PWRHERO11 ZT NWD Dummy | $0.03 | below range | $0.98 | comparable item: S10 ZT NWD Dummy Unit |
| Home | 5108000126 PowerForce Pet Turbo XL NWD | $0.03 | below range | $58.33 | comparable item: Bissell Powerforce Turbo |
| Home | 5108000127 PowerForce Pet XL NWD | $0.03 | below range | $0.98 | comparable item: Pet Hair Eraser DualBrush NWD |
| Home | 19862859913 BISSELL PowerClean DualBrush Stick Vacuum Non-Working Display | $0.03 | below range | $23.44 | comparable item: BISSELL 3-in-1 Stick Vacuum 2030B |
| Home | 19866965750 PowerLifter Allergen NWD | $0.03 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 14804252237 Thyme & Table Pod Machine Display | $0.02 | below range | $17.69 | median price of the same kind of item |
| Home | 15629322702 Thyme & Table Coffee Backer Card | $0.02 | below range | $25.45 | median price of the same kind of item |
| Home | 15702410434 Thyme & Table Heated Backer Card | $0.02 | below range | $17.69 | median price of the same kind of item |
| Home | 15750754422 Thyme & Table Coffee Holder Display Rack | $0.02 | below range | $14.05 | comparable item: Single Serve Coffee Display Rack |
| Home | 968973054 36IN TIRE RACK | $0.02 | below range | $64.35 | comparable item: Frigidaire 16 In. Rack 316067902 |
| Home | 362152140 Hoover Cruise Display | $0.02 | below range | $30.00 | median price of its category |
| Home | 1477877746 Chefman Anti-Overflow Belgian Waffle Maker, Black - POP Display | $0.02 | below range | $39.70 | comparable item: CHEFMAN ANTI-OVERFLOW BELGIAN WAFFLE MAKER, TEMPER |
| Home | 14751101561 Thyme & Table Toaster Display | $0.02 | below range | $23.52 | comparable item: Proctor Silex 22335 Toaster |
| Home | 14754472921 Thyme & Table Espresso Machine Display | $0.02 | below range | $9.99 | comparable item: RSVP International Espresso Machine Brush |
| Home | 14769601100 Thyme & Table Countertop Blender Display | $0.02 | below range | $56.84 | comparable item: Nutribullet Countertop Blender |
| Home | 14799904777 Thyme & Table Single Serve Blender Display | $0.02 | below range | $14.88 | comparable item: Hamilton Beach Single-Serve Blender |
| Home | 14803756258 Thyme & Table Slow Cooker Display | $0.02 | below range | $57.78 | comparable item: Crock-Pot Slow Cooker |
| Home | 14804202617 Thyme & Table Mini Espresso Machine Display | $0.02 | below range | $48.47 | median price of the same kind of item |
| Home | 106551826 Black & Decker B&d Cm2020b Non-working Display Sample | $0.01 | below range | $49.88 | comparable item: Black & Decker CM5050 Coffemaker |
| Home | 133542987 Black & Decker Bd 400w Juice Extractor Display | $0.01 | below range | $36.30 | comparable item: Black & Decker Fruit & Vegetable Juice Extractor |
| Home | 144413136 CO2 Gravity Feeder 18ct | $0.01 | below range | $23.80 | median price of the same kind of item |
| Home | 163102287 POP DISPLAY 13 PC Cutlery Block Set | $0.01 | below range | $69.38 | comparable item: Ginsu 14 Pc. Natural Block Cutlery Set |
| Home | 166488582 Black & Decker B&d Xl Toaster Oven Display | $0.01 | below range | $58.82 | comparable item: Black & Decker Toaster Oven |
| Home | 199064588 Hamilton Beach Hb 12c Easy Access Coffee Maker Display | $0.01 | below range | $46.99 | comparable item: Hamilton Beach Programmble Easy Access Plus Coffee |
| Home | 225462904 Jack Lalanne Juicer Ss Display | $0.01 | below range | $13.43 | comparable item: Hamilton Beach 1.1 MWO SS DISPLAY |
| Home | 236960827 DPLY SHELL KEUR BRWR KSPR BLK DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 241668639 DSPBL780WMP DISPLAY | $0.01 | below range | $0.98 | comparable item: Display Crispi four qt, DSPFN100WMP |
| Home | 247865541 Mr. Coffee Mc Barista Plexi Display | $0.01 | below range | $18.70 | median price of the same kind of item |
| Home | 264621838 Black & Decker Bd Souvide Dis | $0.01 | below range | $34.20 | comparable item: Black & Decker Bd 4 In 1 Coffermaker W&g |
| Home | 277473536 Bella Copper Waffle Disp | $0.01 | below range | $41.26 | comparable item: Bella Copper Ceramic Coated Waffle Maker |
| Home | 289196175 George Foreman Gf 60 Grill Display | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 307647771 Soda Stream Play Kit Display Black | $0.01 | below range | $17.52 | median price of the same kind of item |
| Home | 313894488 Mr Coffee 3qt Ice Teamakr Display | $0.01 | below range | $18.70 | median price of the same kind of item |
| Home | 323848619 Black & Decker Bd 8cup Food Processor Display | $0.01 | below range | $46.97 | comparable item: Black & Decker Bd 8 Cup Food Processor |
| Home | 345583386 BlendJet2 Display- Walmart | $0.01 | below range | $17.99 | median price of its category |
| Home | 349942383 Farberware Fp3000fbs Non-working Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 369572515 Hamilton Beach Display For Hb Sodastation | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 380549503 Espressotoria Caprista Display White | $0.01 | below range | $99.00 | comparable item: Espressotoria Caprista White Espresso Coffee Pod M |
| Home | 382299747 Oster Party Jar Blendr W/ss Cup Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 389454447 Black & Decker Digital Extra-wide Toaster Oven, Gray | $0.01 | below range | $86.87 | comparable item: Black + Decker Extra-Wide Toaster Oven Stainless S |
| Home | 389570223 Jack Lalanne Power Cooker Display 8qt | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 391399679 Mr Coffee 5 Cup Coffeemkr Display | $0.01 | below range | $19.36 | comparable item: Mr. Coffee 5 Cup Coffee Maker |
| Home | 400767049 Presto Frydaddy Elite Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 413540224 Black & Decker B&d 4 Slice, 2 Knob, Black Oven Display | $0.01 | below range | $37.80 | comparable item: Black & Decker 4 Slice Toaster Oven |
| Home | 427670440 Black & Decker B&d 2sl Blk Display | $0.01 | below range | $0.98 | comparable item: Black + Decker Quiet Blender Display |
| Home | 431137927 Medelco Café Brew Pour Over Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 431744881 Ninja Food Processor Display | $0.01 | below range | $99.00 | comparable item: Hamilton Beach 70595 Food Processor |
| Home | 432017770 Yukon Charlies Tray For Max Security Modular | $0.01 | below range | $17.99 | median price of its category |
| Home | 441362223 Black & Decker B&d Oven Blk Display | $0.01 | below range | $58.82 | comparable item: Black & Decker Toaster Oven |
| Home | 472295026 Jack Lalanne Juicer Display | $0.01 | below range | $9.87 | comparable item: Hangrees-The Juicer |
| Home | 493064118 Bunn Speed Brew Csb2 10 Cup Coffee Displ | $0.01 | below range | $16.07 | comparable item: BUNN 42683 8-Cup Glass Carafe for Phase Brew HG Ho |
| Home | 561236883 Hamilton Beach Dsp Expert Toast | $0.01 | below range | $17.99 | median price of its category |
| Home | 569610708 Puffy Tray Liner, 4.25 Oz. | $0.01 | below range | $30.00 | median price of its category |
| Home | 575604193 Black & Decker B & D Can Opener, Smp, Black Display | $0.01 | below range | $19.00 | comparable item: Black & Decker Can Opener |
| Home | 583204601 Black & Decker B&d Je2200b Non-working Display Sample | $0.01 | below range | $17.99 | median price of its category |
| Home | 585025428 Black & Decker B&d 2sl Red Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 594826717 Black & Decker Cm5000b Non-working | $0.01 | below range | $49.88 | comparable item: Black & Decker CM5050 Coffemaker |
| Home | 617335488 Mr. Coffee Mc Glass Ice Tea Maker Display | $0.01 | below range | $23.89 | comparable item: Mr Coffee Ice Tea Maker - Lime |
| Home | 617977106 George Foreman Grill Nw Dis | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 629074747 Presto Fountain Popper Display | $0.01 | below range | $37.00 | comparable item: Presto Electric Hot Air Fountain Popper |
| Home | 638700995 Oster Werrington Stainless Steel Cutlery Set, 12 Piece | $0.01 | below range | $32.44 | comparable item: Oster 6 Piece Black Stainless Steel Cutlery Set |
| Home | 641685101 Ninja Product Display | $0.01 | below range | $15.60 | comparable item: American Standard Product 047194-0070A |
| Home | 645466074 Me Turbo Convection Oven - Ds | $0.01 | below range | $17.99 | median price of its category |
| Home | 658722427 Aroma Ar 20c Ss Display | $0.01 | below range | $13.43 | comparable item: Hamilton Beach 1.1 MWO SS DISPLAY |
| Home | 679964260 Ninja Air Grill Display | $0.01 | below range | $35.93 | median price of the same kind of item |
| Home | 680732209 Services Fusion Juicer Display | $0.01 | below range | $19.99 | median price of the same kind of item |
| Home | 690920617 BD 6SL AIR FRYER TOASTER OVEN DISPLAY | $0.01 | below range | $84.06 | comparable item: Chefman 18L Toaster Oven Air Fryer, New |
| Home | 712641438 Mainstays Mainstay Griddle Display | $0.01 | below range | $15.03 | comparable item: Mainstay 11" Griddle, Red |
| Home | 750373045 Plaid 11 Slot Left Paint Tray, 8 Fl. Oz. | $0.01 | below range | $17.99 | median price of its category |
| Home | 753659820 Black & Decker B&d Oven Ss Display | $0.01 | below range | $58.82 | comparable item: Black & Decker Toaster Oven |
| Home | 758021341 Mainstays 0.7cf/700w Mwo | $0.01 | below range | $14.16 | comparable item: Mainstays Ms 0.7 Cf Blk Mwo Dis |
| Home | 761630260 Gameday Outfitters Tray For 4' Modular | $0.01 | below range | $19.99 | comparable item: Better Homes & Gardens Tray |
| Home | 769495807 Mr. Coffee Ice Tea Maker Display | $0.01 | below range | $23.89 | comparable item: Mr Coffee Ice Tea Maker - Lime |
| Home | 785173079 Mainstays 0.7cf/700w Mwo | $0.01 | below range | $14.16 | comparable item: Mainstays Ms 0.7 Cf Blk Mwo Dis |
| Home | 807245993 Mr. Coffee Mc Esprsso Plexi Display | $0.01 | below range | $18.70 | median price of the same kind of item |
| Home | 826104219 Farberware Royalty Fw Toaster Oven Display | $0.01 | below range | $22.86 | comparable item: Farberware Royalty Farberware 2 Slice Toaster |
| Home | 844446169 Mainstays Display Mwo | $0.01 | below range | $16.30 | comparable item: MAINSTAYS 1.1 MWO DISPLAY |
| Home | 847267217 Bella Extra Large Grill Display | $0.01 | below range | $33.23 | median price of the same kind of item |
| Home | 850145128 Crock-pot Cp Hook Up 3.5qt Oval Display | $0.01 | below range | $50.83 | comparable item: Crock-Pot Hook Up SCCPMD1-CP - Slow cooker - 2 qt  |
| Home | 854901872 Sled Display - Acrylic | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 866136387 Brim Ceramic Skillet Display | $0.01 | below range | $29.84 | comparable item: Bella Ceramic Skillet |
| Home | 866915815 Hamilton Beach Hb Big Mouth Juicer Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 869335545 BD 4 SL AIR FRY TOASTER OVEN DISPLAY | $0.01 | below range | $84.22 | comparable item: GreenLife Air Fry Toaster Oven | Turquoise |
| Home | 871234713 Cuisinart 5n1 Grill Display | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 894709922 Tramontina Pop Display For 4pc Induction Cooking | $0.01 | below range | $76.90 | comparable item: Tramontina Portable Induction 4 Piece Cooking Syst |
| Home | 896561924 Paula Deen Red Cutlery Display | $0.01 | below range | $0.97 | comparable item: Red Cutlery |
| Home | 933072185 Jack Lalanne Copper Chef Skillet Display | $0.01 | below range | $29.99 | median price of the same kind of item |
| Home | 974696034 Aroma Ar 8c Rice Display | $0.01 | below range | $29.98 | median price of the same kind of item |
| Home | 995874252 Puffy 7 Slot Tray Liner, 4.25 Fl. Oz. | $0.01 | below range | $17.99 | median price of its category |
| Home | 1230663676 Rise By Dash Egg Bite Maker Display | $0.01 | below range | $24.97 | comparable item: Salton Egg Bite Maker - 4 Bite |
| Home | 1530519110 Display for Aroma 20 Cup Rice Cooker ARC-390NGP-POP | $0.01 | below range | $33.91 | comparable item: Aroma Housewares ARC-730G 20 Cup Rice Cooker |
| Home | 1771441537 WALMART HEADER DISPLAY 2023 USA | $0.01 | below range | $17.99 | median price of its category |
| Home | 1936191576 Display Big Kitchen Kettle | $0.01 | below range | $38.37 | comparable item: Presto Kitchen Kettle Multi-Cooker |
| Home | 2166127675 DISPLAY Aroma Professional 20Cup RC ARC1240W | $0.01 | below range | $41.44 | comparable item: Aroma Professional ARC-1000 Cooker & Steamer |
| Home | 2468538421 Display for Aroma 6 Cup Rice Cooker ARC-393NG-POP | $0.01 | below range | $33.91 | comparable item: Aroma Housewares ARC-730G 20 Cup Rice Cooker |
| Home | 2979568032 Display Presto Pizza Oven | $0.01 | below range | $16.52 | median price of the same kind of item |
| Home | 3046610703 COSORI 5.0-Quart Rice Cooker with 9 Cooking Functions, Touch Control,  | $0.01 | below range | $85.32 | comparable item: COSORI 5.0-Quart Rice Cooker with 9 Cooking Functi |
| Home | 5055219449 Ultima Cosa Soda Maker DSP | $0.01 | below range | $49.99 | comparable item: Ultima Cosa Presto Frizzante Soda Maker- Black |
| Home | 5129928207 Ember 2023 Mug Display | $0.01 | below range | $14.98 | median price of the same kind of item |
| Home | 5164703312 Display Presto 16 " Ceramic Skillet | $0.01 | below range | $59.99 | comparable item: 12" Folding Ceramic Skillet |
| Home | 5166665530 DSPMC1100WMP display | $0.01 | below range | $0.98 | comparable item: Display Crispi four qt, DSPFN100WMP |
| Home | 5212541991 Chefman ExacTemp 12 Quart Air Fryer w/ Thermometer POP Display | $0.01 | below range | $94.74 | comparable item: Chefman Turbofry Touch Family Size Air Fryer, 8 Qu |
| Home | 5275954304 INP 7.5QT PRESSURE NWD | $0.01 | below range | $81.05 | comparable item: Instant Pot 6QT Easy 3-in-1 Slow Cooker, Pressure  |
| Home | 5671224294 MS Certified Glass Blender with Versatile Speeds and Accessories | $0.01 | below range | $11.16 | comparable item: MS GLASS BLENDER DIS |
| Home | 12998854355 Ninja Pod Rack Graphic Display Refresh, INSWCFDIS8WM | $0.01 | below range | $17.99 | median price of its category |
| Home | 13052761043 Chef iQ Smart Thermometer 1-Probe Display | $0.01 | below range | $99.67 | comparable item: Chef iQ Smart Thermometer |
| Home | 13067062469 Chef iQ 6 Quart Smart Multicooker Display NG | $0.01 | below range | $17.99 | median price of its category |
| Home | 13289508019 Black + Decker Food Processor Display | $0.01 | below range | $46.97 | comparable item: Black & Decker Bd 8 Cup Food Processor |
| Home | 13777205136 Ninja Creami Swirl Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 14267867363 Ninja Drip/Coffeemaker Display | $0.01 | below range | $30.00 | comparable item: Proctor-Silex 48571 Automatic Drip Coffeemaker |
| Home | 14284357312 Ninja Drip/Coffeemaker Display | $0.01 | below range | $30.00 | comparable item: Proctor-Silex 48571 Automatic Drip Coffeemaker |
| Home | 14737472657 Chef iQ Smart Thermometer 1 V3 Probe Display | $0.01 | below range | $99.67 | comparable item: Chef iQ Smart Thermometer |
| Home | 14768903848 Beautiful 10 in 1 Multi-Cooker, White Icing, NON-WORKING DISPLAY | $0.01 | below range | $11.00 | median price of the same kind of item |
| Home | 19000857004 ECP3630 DISPLAY | $0.01 | below range | $17.99 | median price of its category |
| Home | 19195868995 Display Pressure Cooker Sage - DSPPC200WMP | $0.01 | below range | $11.61 | median price of the same kind of item |
| Home | 321765920 SB3651-E6 POP | $0.01 | below range | $17.88 | median price of the same kind of item |
| Home | 775583126 JDZDESIGN 3M Scotchgard Down Alternative All Season Comforter Set | $0.01 | below range | $42.99 | comparable item: fangmm 3-Piece All-Season Down Alternative Comfort |
| Home | 315330010 Lime Crime 4 foot empty replacement tray | $0.01 | below range | $30.00 | median price of its category |
| Home | 369141527 bubly Towel | $0.01 | below range | $23.79 | median price of the same kind of item |
| Home | 20613753 Mainstays Silicone Red Zigzag Trivet | $0.01 | below range | $3.88 | comparable item: Mainstays Red Silicone Trivet |
| Home | 469220667 CO2 Wire Rack 48ct | $0.01 | below range | $59.55 | comparable item: Foreside Home and Garden Farmhouse Wire Rack |
| Home | 507997499 Hamilton Beach Fullsize Iron Display | $0.01 | below range | $21.91 | comparable item: Hamilton Beach Steam Iron 14672 |
| Home | 638551525 Better Homes & Gardens Display Better Homes & Gardens Ellis Shutter Ca | $0.01 | below range | $32.87 | median price of the same kind of item |
| Home | 850573944 Freestanding Rack For 54" Yard Goods, 16 | $0.01 | below range | $30.00 | median price of its category |
| Home | 889956036 Hamilton Beach HB RETRACTABLE CORD IRON | $0.01 | below range | $19.94 | comparable item: Hamilton Beach Retractable Cord Iron | Model# 1428 |
| Home | 5144555098 Chi Lava Iron with Retractable Cord Display | $0.01 | below range | $69.98 | comparable item: CHI Iron with Retractable Cord | Model# 13106 |
| Home | 5144555099 CHI 360 Precision Steam Iron with Retractable Cord Display | $0.01 | below range | $69.98 | comparable item: CHI Iron with Retractable Cord | Model# 13106 |
| Home | 14584273355 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14603474727 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14609117856 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14609167619 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14613958917 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14614008894 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14617104925 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14620013239 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14620811860 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 14621614137 new display | $0.01 | below range | $30.00 | median price of its category |
| Home | 101634849 Hamilton Beach Hb 8qt Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 103646099 Shark Sh Apex 2.0 Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 103909329 Oster Classic Black Blender Display | $0.01 | below range | $33.69 | comparable item: Oster Classic 3-Speed Blender, Smoothie Blender, B |
| Home | 105703152 Hoover Hv Power Scrub Elite Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 105718023 BISSELL Powerglide Liftoff Pet | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 105887390 Shark Display Rv750wm | $0.01 | below range | $30.00 | median price of its category |
| Home | 106331941 Black & Decker Lithium 2in1 Display | $0.01 | below range | $98.00 | comparable item: Black And Decker 18v Lithium Pivot, Bdh |
| Home | 111554777 Oster Belgian Waffle Display | $0.01 | below range | $28.00 | comparable item: Oster® DiamondForce™ Nonstick Belgian Waffle Maker |
| Home | 111966192 BI PET HAIR ERASER SLIM CORDLESS NWD | $0.01 | below range | $6.49 | comparable item: BISSELL Pet Stain Eraser NWD |
| Home | 114077922 BISSELL Bagged Pet Powerlifter | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 115046998 Hamilton Beach Flexbrew Display | $0.01 | below range | $8.07 | comparable item: Hamilton Beach FLEXBREW GEN 4 TRIO DISPLAY |
| Home | 118665244 BISSELL Revolution Pet Pro Vacuum | $0.01 | below range | $28.63 | comparable item: BISSELL Pet Pack Vacuum Attachments, 3260 |
| Home | 121492398 Hamilton Beach 5 Quart Oval Stainless Steel Slow Cooker | $0.01 | below range | $33.43 | comparable item: Chefman 7-Quart Stainless Steel Slow Cooker, Oval |
| Home | 123633892 Hamilton Beach Hb Hand Mixer W/case Display | $0.01 | below range | $19.84 | comparable item: Hamilton Beach Black Hand Mixer with Storage Case |
| Home | 128877236 Black & Decker Bd 2 Sl Blk Ss Toaster Display | $0.01 | below range | $24.97 | comparable item: Black & Decker Bd Dillybean 2s Toaster White |
| Home | 129450982 BISSELL Spotclean Proheat Pet Vacuum Cleaner | $0.01 | below range | $8.51 | comparable item: To Fit BISSELL PROHeat Vacuum Cleaner Belts for BI |
| Home | 130389835 Oster Jellybean 2 Slice Toaster | $0.01 | below range | $34.99 | comparable item: Oster® 2-Slice Toaster |
| Home | 131050906 Eureka Display Simply Clean Upright | $0.01 | below range | $95.10 | comparable item: Eureka Extreme Clean Upright Vacuum |
| Home | 133577039 Shark Rotator Pla Duoclean Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 138411774 Hoover Hv Spotless Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 140570472 George Foreman 84in Grill Display | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 141168893 Mr Coffee Espresso Maker Ss Display | $0.01 | below range | $50.77 | comparable item: Mr. Coffee 4 Cup Espresso Maker |
| Home | 141936108 Display Krups 4 Slice Toaster Ss | $0.01 | below range | $90.98 | comparable item: Krups Savoy 4 Slice Toaster |
| Home | 142090791 Oster Hand Mixer Display | $0.01 | below range | $20.16 | comparable item: Betty Crocker Hand Mixer |
| Home | 145330729 Dyson V6 Motorhead Origin Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 146032182 Hoover Hv React Pro Pet Display | $0.01 | below range | $13.97 | comparable item: HV Oxy Pet Portable Form |
| Home | 146964673 Ninja Performance Blender Display | $0.01 | below range | $39.21 | comparable item: Farberware Performance Blender |
| Home | 148879301 Hoover Hv Rewind Blue Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 151037691 Hoover Hv React Powered Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 152023284 Electrolux Display Ergorapido Stick | $0.01 | below range | $89.93 | comparable item: Electrolux Ergorapido EL 1010A - Vacuum cleaner -  |
| Home | 152603441 ZD400 DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 156504824 Black & Decker Wifi Slow Cooker Display | $0.01 | below range | $42.93 | median price of the same kind of item |
| Home | 157071869 Eufy RoboVac G30 Display | $0.01 | below range | $29.99 | comparable item: Eufy RoboVac Replacement Kit |
| Home | 157147117 Krups Deep Fryer Display | $0.01 | below range | $2.84 | comparable item: Farberware Deep Fryer Display |
| Home | 163739709 Hamilton Beach Hb Soft Scrapes Hand Mixer Display | $0.01 | below range | $18.74 | comparable item: Refurbished Hamilton Beach® Hand Mixer |
| Home | 163835790 Instant Pot Vortex 6Qt Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 165175103 Hoover Hv React Compact Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 168382294 Bissell Crosswave Nwd | $0.01 | below range | $1.00 | comparable item: BISSELL CROSSWAVE HF3 NWD |
| Home | 172650626 INP 5QT AF DISPLAY | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 172863096 Jack Lalanne Power Pressure Cooker 10qt Display | $0.01 | below range | $57.26 | comparable item: Better Chef 6QT Pressure Cooker |
| Home | 174168915 Display Krups Waffle Maker | $0.01 | below range | $11.78 | comparable item: Cocina Criolla Waffle Maker |
| Home | 174362573 Dirt Devil Dd Reach Max Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 176042501 Hoover Display Hvr Rewind Bagless Upright | $0.01 | below range | $88.00 | comparable item: Hoover Rewind Bagless Upright Vacuum Cleaner, UH71 |
| Home | 176225359 Hoover Hv Quest 600 Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 179070370 Dirt Devil Dd Power Swerve Disp | $0.01 | below range | $89.99 | comparable item: Dirt Devil Power Swerve 16V Cordless Stick Vacuum, |
| Home | 179921474 Bissell Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 182742914 Bissell Airram Nwd | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 183613517 Bissell Robot Vacuum Nwd | $0.01 | below range | $39.96 | comparable item: BISSELL Easy Vacuum |
| Home | 184132736 DPLY SLED KEUR BRWR KEXPE BLUE | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 186508055 Shark Rotator Powered Lift-away Speed Display | $0.01 | below range | $71.34 | comparable item: Shark® Rotator® Powered Lift-Away® Speed with Self |
| Home | 188718121 Bissell Spinwave Nwd | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 192577891 Hoover Powerdash Barefloor Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 192677811 Black & Decker Smartech Lift Off Display | $0.01 | below range | $17.93 | comparable item: Black and Decker 90555840 Wall Base |
| Home | 195064183 Dirt Devil Dd Power Max Xl Disp | $0.01 | below range | $67.19 | comparable item: Dirt Devil Power Max XL Upright Bagless Vacuum, UD |
| Home | 195532998 Bissell Little Green Pro Nwd | $0.01 | below range | $98.00 | comparable item: Bissell Little Green Pro Heat Turbo Pet |
| Home | 196021393 DSPNV150WMP Display | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 196697243 Hoover Hv Power Scrub Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 199395887 Display Krups 2 Slice Toaster | $0.01 | below range | $90.98 | comparable item: Krups Savoy 4 Slice Toaster |
| Home | 200302381 Samsung 1.4cf Mwo Display | $0.01 | below range | $7.49 | comparable item: Hamilton Beach Display Mwo |
| Home | 200384072 Tax Time Deals! | $0.01 | below range | $17.99 | median price of its category |
| Home | 201251260 Instant Pot Vortex Mini 2Qt Red Display | $0.01 | below range | $49.92 | comparable item: Instant™ Vortex™ Mini Air Fryer 2 Quart 4-in-1, Aq |
| Home | 201419807 Ninja Foodi 8 Qt Display | $0.01 | below range | $24.99 | comparable item: Ninja Foodi 6.5-Qt. Ceramic-Coated Inner Pot 102FY |
| Home | 201886459 DSPCM300WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 202342699 Bissell Bi Powerlifter Pet Rewind Nwd | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 208988311 Kitchenaid 4.5qt Classic Mixer Black Dis | $0.01 | below range | $59.00 | comparable item: Kalorik M 21847 - Mixer - 3.2 qt - 200 W - black/c |
| Home | 210529337 PowerXL Vortex Pro Air Fryer Plus 8 Quart Display | $0.01 | below range | $89.00 | comparable item: PowerXL Vortex Pro 8 Qt Air Fryer |
| Home | 214655836 Hamilton Beach Disply | $0.01 | below range | $17.99 | median price of its category |
| Home | 215150770 Ninja Coffeemaker Black Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 215393493 Floor One S2 NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 217043972 Power Xl Pxl Vortex Air Fryer 10qt Dummy | $0.01 | below range | $89.00 | comparable item: PowerXL Vortex Pro 8 Qt Air Fryer |
| Home | 217411962 Hamilton Beach Hb 1 Liter Kettle Display Ss | $0.01 | below range | $24.99 | comparable item: Hamilton Beach 1.8 Liter Cordless Kettle. |
| Home | 219427125 Hoover Total Home Pet Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 220554925 Mr. Coffee Display,cffemkr,mrc,12c,pg,red | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 220776067 KES6403BM Espresso Display | $0.01 | below range | $18.27 | median price of the same kind of item |
| Home | 221867315 Hamilton Beach Hb Glass Jar Blender Black Ss Display | $0.01 | below range | $54.99 | comparable item: Hamilton Beach Smoothie Smart Blender, Glass Jar,  |
| Home | 223892164 Mr. Coffee $89 Espresso Plexi Display | $0.01 | below range | $22.75 | median price of the same kind of item |
| Home | 224409869 Hoover Display Hvr Air Elite Duuh72460 | $0.01 | below range | $30.00 | median price of its category |
| Home | 228982793 PowerXL Boost Blender Plus Display | $0.01 | below range | $57.99 | comparable item: PowerXL™ Boost Blender Plus™ 4 Speed, 800 Watts, 4 |
| Home | 229290476 SHARK 10" IN LINE VM200 DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 229950762 Oster Big Jar Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 234873070 Cosori 5.8qt Smart Air Fryer Display for Stores | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 237951196 Mr Coffee 5 Cup Coffeemaker Display | $0.01 | below range | $52.13 | comparable item: Mr. Coffee 14-Cup Stainless Coffeemaker |
| Home | 238879193 DPLY SLED KEUR BRWR KEXPE RED DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 240690272 George Foreman Gf Gr2081hm Non-working Display Sample | $0.01 | below range | $19.88 | median price of its category |
| Home | 243780478 Ninja Air Fryer Display | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 246289586 Shark Ion Force Zero-m Stick Vac Display | $0.01 | below range | $49.86 | comparable item: Shark Bagless Stick Vac |
| Home | 246442946 Dyson Light Ball Mf Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 247340008 Beautiful 2SL Toaster WHITE NON-WORKING DISPLAY | $0.01 | below range | $36.99 | median price of the same kind of item |
| Home | 247433325 Dyson - V6 Mtohd Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 248327319 Hoover Display Hvr Steam Vac | $0.01 | below range | $30.00 | median price of its category |
| Home | 249989539 Oster Skillet Ost Dm Display Wm | $0.01 | below range | $29.99 | median price of the same kind of item |
| Home | 251347075 George Foreman 60in Grill Display | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 251954134 Presto Kitchen Kettle Display | $0.01 | below range | $38.37 | comparable item: Presto Kitchen Kettle Multi-Cooker |
| Home | 253177211 Emerils Emerillagasse Pressure Airfryer Plus Dis | $0.01 | below range | $17.99 | median price of its category |
| Home | 253871926 Bissell Bi Pet Hair Eraser Slim Corded Nwd | $0.01 | below range | $6.49 | comparable item: BISSELL Pet Stain Eraser NWD |
| Home | 254633452 Mr Coffee 10c Coffeemkr Dis | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 256898138 Fw Air Fryer Display | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 257131502 Hamilton Beach D14pl 1.1 Cf/1000w Microwave Display | $0.01 | below range | $62.42 | comparable item: Emerson .9cf Microwave |
| Home | 257612903 Bissell Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 259691161 Kitchenaid 7cup Food Processor Display | $0.01 | below range | $39.99 | comparable item: KitchenAid 3.5 Cup Mini Food Processor |
| Home | 260175382 Shark Rotator Pla Zerom Speed Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 260306520 B 6QT AIRFRY DISPLAY | $0.01 | below range | $0.98 | comparable item: Thyme & Table 6 QT Air Fryer Display |
| Home | 266567272 Hamilton Beach Hb 2slice Toaster Display | $0.01 | below range | $49.53 | comparable item: Hamilton Beach Hb 6 Slice Toaster Oven |
| Home | 267729592 Mr. Coffee 24oz Single Serve Coffee Dis | $0.01 | below range | $69.00 | comparable item: Mr Coffee 24oz Single Serve Coffee Maker |
| Home | 268547457 Brim Silver Kettle Display | $0.01 | below range | $60.96 | comparable item: Bella 1.2 L Silver Ceramic Kettle |
| Home | 271118068 Bissell Bi Powerforce Powerbrush Pet Nwd | $0.01 | below range | $91.00 | comparable item: Bissell Bi Powerforce Helix Turbo Rewind Nwd |
| Home | 272323596 Bodum 12 Cup Pour Over Coffee Maker with Permanent Filter | $0.01 | below range | $19.82 | comparable item: Bodum 8 Cup Black Pour Over Coffee Maker with Perm |
| Home | 273717714 Sunbeam Stand Mixer Display | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 274017819 CUISINART Automatic Grind & Brew 12-Cup Coffeemaker DISPLAY | $0.01 | below range | $77.72 | comparable item: Restored Cuisinart Grind and Brew 12-Cup Coffeemak |
| Home | 274968747 Mr Coffee 12c Speed Brew Slate Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 276645915 Display Shark Rocket Zero M | $0.01 | below range | $30.00 | median price of its category |
| Home | 276787286 Mainstays 0.7 Cu Ft White Microwave Oven | $0.01 | below range | $65.00 | comparable item: Mainstays 0.7 Cu. Ft. 700W Compact Microwave Oven, |
| Home | 277148543 Oster Personal Blendr Dis | $0.01 | below range | $17.99 | median price of its category |
| Home | 278032626 FW 6QT PRESSURE COOKER NWD | $0.01 | below range | $59.00 | comparable item: FW 6QT PRESSURE COOK |
| Home | 278977533 Oster Griddle Ost Dm Display Wm | $0.01 | below range | $32.45 | median price of the same kind of item |
| Home | 282926744 Bissell Powerforce Bagged Nwd | $0.01 | below range | $35.28 | comparable item: Bissell PowerForce Bagged Upright Vacuum, 1739 |
| Home | 283138929 Black & Decker Smartech 2-in-1 Display | $0.01 | below range | $19.94 | median price of the same kind of item |
| Home | 283150010 Emeril Lagasse 6 Quart Pressure Air Fryer | $0.01 | below range | $72.99 | comparable item: Sboly 6-Quart Air Fryer |
| Home | 285869767 Shark Cyclone Hand Vac Display | $0.01 | below range | $57.00 | comparable item: Shark VX33 18V Bagless Hand Vac |
| Home | 285871877 CUISINART COMPACT GRIDDLER DISPLAY | $0.01 | below range | $17.99 | median price of its category |
| Home | 286604141 Hoover Hv Pet Upright Disp | $0.01 | below range | $13.97 | comparable item: HV Oxy Pet Portable Form |
| Home | 287083540 Hoover Smartwash Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 287468444 Sharp Countertop Microwave 1.8cf Display | $0.01 | below range | $82.98 | comparable item: Sharp .7 Cf Ss Microwave Oven |
| Home | 290013544 Black & Decker Steam Mop Display | $0.01 | below range | $10.00 | comparable item: Black & Decker Steam Iron |
| Home | 290165487 Kitchenaid Deluxe Stand Mixer Slvr Dis | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 303144976 BI PROHEAT PET TURBO NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 304334359 Dyson Dy V6 Cordfree Origin Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 306567595 LA500 DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 307025618 Oster Personal Blendr Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 307461311 Hamilton Beach Hb 4 Slice Toaster Oven Red Display | $0.01 | below range | $49.53 | comparable item: Hamilton Beach Hb 6 Slice Toaster Oven |
| Home | 307796703 Kitchenaid 12cup Coffeemaker Display | $0.01 | below range | $69.98 | comparable item: Better Chef 10-50 Cup Coffeemaker |
| Home | 309050064 Bunn 10 Cup Coffeemaker Display | $0.01 | below range | $69.98 | comparable item: Better Chef 10-50 Cup Coffeemaker |
| Home | 309449019 Dyson Dc33 Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 309739872 DSPHV370WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 311291200 DSPSS400WM | $0.01 | below range | $17.99 | median price of its category |
| Home | 312439663 Hoover Hv Impulse Stick Vac Display | $0.01 | below range | $65.99 | comparable item: Hoover Presto Stick Vac, BH20095 |
| Home | 313571155 Bissell Bi Powerforce Compact Nwd | $0.01 | below range | $36.52 | comparable item: POWERFORCE COMPACT |
| Home | 313595039 Frigidaire Display Frig 1.6 Ss Mwo | $0.01 | below range | $13.43 | comparable item: Hamilton Beach 1.1 MWO SS DISPLAY |
| Home | 314059018 RugDoctor Deep Carpet Cleaner | $0.01 | below range | $19.97 | comparable item: RugDoctor Oxy-Stem Carpet Cleaner, 60 Oz. |
| Home | 314798522 Oster Os Duraceramic Griddle Display | $0.01 | below range | $37.11 | comparable item: Oster DuraCeramic Griddle |
| Home | 319515719 SHARK STEAM SCRUB DISPLAY | $0.01 | below range | $99.99 | comparable item: STEAM MOP 4.0 |
| Home | 327328157 Display Oster Blender 12sp | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 331553518 Cuisinart 4sl Toaster Display | $0.01 | below range | $36.99 | median price of the same kind of item |
| Home | 331980239 Ninja Coffee Maker Display Ss Carafe | $0.01 | below range | $29.71 | comparable item: Coleman Carafe Propane Ss/coffee Maker P |
| Home | 332425027 Hamilton Beach Hb 6qt Probe Display | $0.01 | below range | $48.99 | comparable item: Hamilton Beach 33969 6 qt. Meat Probe Slow Cooker |
| Home | 332876335 Ninja Blender W/cup Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 334539314 Oster Classic Blender Wht Display | $0.01 | below range | $79.98 | comparable item: Classic 3-Speed Oster® Blender |
| Home | 336582368 Cuisinart Stand Mixer Red Display | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 337864027 Presto 3.5l Deepfry Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 340396068 Brim Mainstays 2 Sl Toaster Non-working Disp | $0.01 | below range | $36.99 | median price of the same kind of item |
| Home | 345324864 Bissell Powerlifter Rewind Display | $0.01 | below range | $88.00 | comparable item: Bissell Powerlifter Rewind, 1413 |
| Home | 345488092 Shark Ion Force Corded Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 346013608 Oster Dfl Convection Oven Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 349360641 Oster Os 12 Speed Blender W/fp Display | $0.01 | below range | $69.29 | comparable item: Oster 2 Speed Blender |
| Home | 349934192 Hamilton Beach Hb Digital Kettle Display | $0.01 | below range | $11.95 | comparable item: Hamilton Beach Hb Digital Microwave |
| Home | 353666093 Black & Decker B&d Fp1700b Non-working Display Sample | $0.01 | below range | $17.99 | median price of its category |
| Home | 353944336 Hoover Display Hvr Dual Power Max | $0.01 | below range | $30.00 | median price of its category |
| Home | 355152954 Services Power Liftway Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 355884930 Hamilton Beach Hb 1.1 Mwo | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 356965855 Pure One Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 357084582 Crock-Pot display 4.5 hinged Blk Pr | $0.01 | below range | $37.75 | median price of the same kind of item |
| Home | 357338320 Hamilton Beach Hb Pw Non Working Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 357486600 Crock-pot Cp Hook Up 2qt Round Display | $0.01 | below range | $50.83 | comparable item: Crock-Pot Hook Up SCCPMD1-CP - Slow cooker - 2 qt  |
| Home | 359710809 Oster Display 4sl Ss Tstr | $0.01 | below range | $29.92 | comparable item: Oster 2sl Ss Design For Life Toaster |
| Home | 361997669 Hamilton Beach Hb 2 In 1 Oven Display | $0.01 | below range | $49.53 | comparable item: Hamilton Beach Hb 6 Slice Toaster Oven |
| Home | 362167420 Galanz 0.7 Retro Blue Mwo Display Sample | $0.01 | below range | $8.69 | median price of its category |
| Home | 362956445 Magic Bullet Nutribullet 600 Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 364659213 Bissell Powerlifter Swivelrewind Nwd | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 365212489 Magic Bullet Display | $0.01 | below range | $7.49 | comparable item: Hamilton Beach Display Mwo |
| Home | 372000611 Hoover Display Dufh51200 For D/p Pro Cw | $0.01 | below range | $30.00 | median price of its category |
| Home | 374950780 B 2SL TOASTER DISPLY | $0.01 | below range | $36.99 | median price of the same kind of item |
| Home | 375652339 Samsung 1.9 Display | $0.01 | below range | $7.49 | comparable item: Hamilton Beach Display Mwo |
| Home | 377697410 NWD_2WCATGRAPHKIT_21 | $0.01 | below range | $30.00 | median price of its category |
| Home | 379453439 Powerxl Vortex Airfryer Plus 7qt Displa | $0.01 | below range | $17.99 | median price of its category |
| Home | 380076131 Instant Pot Duo 6Qt Display | $0.01 | below range | $79.00 | comparable item: Instant Pot Duo 6qt Copper Ss |
| Home | 381357526 Ninja 3-in-1 Cook System Dsp Acry Only | $0.01 | below range | $17.99 | median price of its category |
| Home | 382394817 Hamilton Beach Hb Single Serve Blender Grey Display | $0.01 | below range | $14.88 | comparable item: Hamilton Beach Single-Serve Blender |
| Home | 386284975 DSPHZ600WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 386981665 Services Sh Stm Pkt | $0.01 | below range | $30.00 | median price of its category |
| Home | 387627698 BD QUIET BLENDER WITH PERSONAL JAR DISPLAY | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 388498947 Kitchenaid Kitchen Aid Stand Mixer Black Display | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 388534288 Hoover High Performance Bagless Upright Display | $0.01 | below range | $12.50 | comparable item: Hoover WindTunnel 3 High Performance Upright Pet V |
| Home | 389987258 Dirt Devil Power Max Pet Display | $0.01 | below range | $90.80 | comparable item: Dirt Devil Power Max Pet Upright Vacuum Cleaner, U |
| Home | 393195730 Hoover Display Hvr Air Lift Upright Duuh72510 | $0.01 | below range | $78.55 | comparable item: Restored Hoover Air Lift Bagless Upright Vacuum, U |
| Home | 393362106 Oster Food Processor Ds Odfl | $0.01 | below range | $73.99 | comparable item: Oster Oskar Food Processor |
| Home | 397133700 Jack Lalanne Power Air Fryer Non Working Display | $0.01 | below range | $79.00 | comparable item: Jack Lalanne 3.4 Quart Power Air Fryer |
| Home | 399071797 Keurig Kold Drinkmaker Display | $0.01 | below range | $4.98 | comparable item: Keurig® KOLD™ Fanta® 8 oz, 4/pack |
| Home | 399127500 Mr Coffee 12c Prog Coffee Maker Display | $0.01 | below range | $44.99 | comparable item: Mr. Coffee Coffee Maker |
| Home | 399943910 DSPSS350WM | $0.01 | below range | $17.99 | median price of its category |
| Home | 400268163 Bella Panini Maker Display | $0.01 | below range | $31.77 | comparable item: Bella Panini Maker |
| Home | 401765242 Mr. Coffee Optimal Brew Plexi Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 402489631 Irobot E6 Robot Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 405381226 Bissell Powerlifter Ion Pet Nwd | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 408069019 Black & Decker Bd 2in1 Stick Vac Display | $0.01 | below range | $49.86 | comparable item: Black & Decker 18V Dustbuster Hand Vac |
| Home | 409624878 Shark Ion Robot Display | $0.01 | below range | $64.94 | comparable item: Shark ION Robot® Series Replenishment Kit |
| Home | 410561891 Instant Pot 8qt Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 412310296 Galanz Ga Digital Microwave | $0.01 | below range | $75.91 | comparable item: Hamilton Beach Digital Microwave Oven |
| Home | 412397772 Bissell Smartclean Robot Nwd | $0.01 | below range | $30.00 | median price of its category |
| Home | 413081263 Oster Double Flip Waffle Red Display | $0.01 | below range | $49.96 | comparable item: Oster Double Flip Red Waffle Maker |
| Home | 413459083 Display Hoover Air Cordless Upright | $0.01 | below range | $13.18 | comparable item: Mainstays Upright Display |
| Home | 413642000 Black & Decker Bd Quiet Single Serve Blender Display | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 415096684 Bissell Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 417202019 Oster Os Versa Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 419007532 Black & Decker Bd 12cup Coffeemkr Wht Display | $0.01 | below range | $12.66 | comparable item: Black & Decker Bd Jar 5cup Replacement |
| Home | 419284105 Rowenta Rw Iron Prom Dsp | $0.01 | below range | $1.00 | comparable item: New Display RW Ultimate Iron |
| Home | 420006123 Bissell Powerlifter Swivel Pet Nwd | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 420192048 Instant Pot 6qt Air Fryer Display | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 420545802 DSPCFP300WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 421569530 Shark Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 421623954 BISSELL POWERFRESH NWD | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 422864881 DSPOL500 | $0.01 | below range | $17.99 | median price of its category |
| Home | 426382385 Black & Decker Bd 6slice 12" Oven Display | $0.01 | below range | $37.80 | comparable item: Black & Decker 4 Slice Toaster Oven |
| Home | 430880868 George Foreman Gf Grp2841r Non-working Display Sample | $0.01 | below range | $19.88 | median price of its category |
| Home | 431410533 Hoover Powerdash Portable Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 431837235 Hamilton Beach Disply | $0.01 | below range | $17.99 | median price of its category |
| Home | 433823298 Bissell Proheat Advanced Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 434899776 Cuisinart 2sl Toaster Display | $0.01 | below range | $36.99 | median price of the same kind of item |
| Home | 434995298 Mainstays 4-Slice Black Toaster Oven | $0.01 | below range | $19.98 | comparable item: Mainstays 4 Slice Toaster Oven, Black |
| Home | 435253201 Memorex Display - Nes Vertuoplus Gray | $0.01 | below range | $17.99 | median price of its category |
| Home | 435978776 Hamilton Beach Hb 2sl Modern Chrome Toaster Display | $0.01 | below range | $42.10 | comparable item: Hamilton Beach Modern Chrome 2 Slice Toaster, 2279 |
| Home | 436174611 Instant Multicooker Disp | $0.01 | below range | $17.99 | median price of its category |
| Home | 436479721 Dirt Devil Display Dd Steam & Spray Mop | $0.01 | below range | $59.00 | comparable item: Dirt Devil Quick Clean Spray & Steam Mop, PD11030U |
| Home | 439198590 BLACK+DECKER 6 Cup Rice Cooker Display | $0.01 | below range | $63.99 | comparable item: Cuckoo 12Cup Rice Cooker Display |
| Home | 441547337 Ecovacs Ozmo U2SE Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 446952512 BEAUTIFUL 8QT SLOW COOKER NON-WORKING DISPLAY | $0.01 | below range | $9.82 | comparable item: Pioneer Woman Speckle Design Slow Cooker, Non-Work |
| Home | 448177701 Black & Decker Bd 12 Cup Thermal Coffee Maker Display | $0.01 | below range | $74.99 | comparable item: Black & Decker 8-Cup Thermal Coffee Maker |
| Home | 449045645 BLACK+DECKER Flex 2-in-1 Stick Vacuum | $0.01 | below range | $23.44 | comparable item: BISSELL 3-in-1 Stick Vacuum 2030B |
| Home | 450716660 SHARK VAC DISPLAY | $0.01 | below range | $30.44 | comparable item: 7GAL DISPLAY VAC |
| Home | 450846863 DSPQB3000SSWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 451511752 Instant Pot Duo 8Qt Display | $0.01 | below range | $79.00 | comparable item: Instant Pot Duo 6qt Copper Ss |
| Home | 455444369 Shark Sh Rocket Cordless Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 455451588 Farberware Battery Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 456344040 Mr. Coffee Mc 12c Cfemkr Wh Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 457088816 Beautiful 6qt Air Fryer WHITE NON-WORKING DISPLAY | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 457591368 Ninja Blender W/cup Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 458331151 Instant Pot Viva 6qt Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 464678017 Shark Freestyle Crdlss Stick Vac Dsp | $0.01 | below range | $49.86 | comparable item: Shark Bagless Stick Vac |
| Home | 468634919 Iced Coffee Maker Black Display | $0.01 | below range | $49.00 | comparable item: Mr. Coffee TFTX85 - Coffee maker - black |
| Home | 468820817 Nutribullet Full-Size Blender Display - Matte Black | $0.01 | below range | $67.74 | comparable item: nutribullet® Full Size 56 oz. Blender 1000 Watt, M |
| Home | 470653546 Ninja Xl Oven Dsply | $0.01 | below range | $17.99 | median price of its category |
| Home | 471078632 Conair® Turbo ExtremeSteam® — Steam & Iron 2-IN-1 With Turbo Model GS1 | $0.01 | below range | $19.94 | median price of the same kind of item |
| Home | 472126235 Hamilton Beach Ham Beach Immersion Blender Blk Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 474886404 Black & Decker 4 Slice, 9" Pizza Toaster Oven Ss Dis | $0.01 | below range | $37.80 | comparable item: Black & Decker 4 Slice Toaster Oven |
| Home | 476871489 Services Ss Hf Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 477541151 BI VACUUM ACCESSORY DISPLAY | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 477919873 Hamilton Beach Hb Smoothie Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 480317470 Hamilton Beach 10 Spd Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 480484404 Hamilton Beach Dual Bsm | $0.01 | below range | $30.00 | median price of its category |
| Home | 484331348 Mc 10c Coffeemkr Display | $0.01 | below range | $0.98 | comparable item: Mc 5cup Coffeemkr Dp |
| Home | 489991377 Presto Deep Fryer Display | $0.01 | below range | $2.84 | comparable item: Farberware Deep Fryer Display |
| Home | 491939676 Hamilton Beach Hb 12c Prgm Coffee Maker Display | $0.01 | below range | $68.00 | comparable item: HB TRIO COFFEE MAKER |
| Home | 496130315 nutriBullet® Smart Touch Blender™ 1400W DISPLAY | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 496293267 Pure One S11 Spartan NWD - Final | $0.01 | below range | $30.00 | median price of its category |
| Home | 498151727 Hamilton Beach Display For Hb 2slice Toaster | $0.01 | below range | $49.53 | comparable item: Hamilton Beach Hb 6 Slice Toaster Oven |
| Home | 498297808 Frigidaire Display Frig 1.1 Cu. | $0.01 | below range | $17.99 | median price of its category |
| Home | 499712372 Neato Vacuum Display | $0.01 | below range | $10.99 | comparable item: MagicBag VACUUM |
| Home | 499714086 HART Brushless Stick Vacuum Display | $0.01 | below range | $22.57 | comparable item: BISSELL 3-in-1 Stick Vacuum |
| Home | 500995790 Shark Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 501812817 Presto Big Kettle Display | $0.01 | below range | $48.59 | comparable item: Presto Big Kettle 2.75 Qt. Multi-Cooker/Steamer 06 |
| Home | 504348868 DPLY SLED KEUR BRWR K-SLIM DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K- CAFÉ DISPLAY |
| Home | 509378810 Oster Display Toaster 2 Slice Red | $0.01 | below range | $34.98 | comparable item: Oster 2-Slice Toaster, Metallic Red |
| Home | 509392833 Mr Coffee 12c Coffee Maker Wh Dis | $0.01 | below range | $44.99 | comparable item: Mr. Coffee Coffee Maker |
| Home | 511308611 Kitchenaid Deluxe Stand Mixer Blue Dis | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 512880545 DSPBN800 | $0.01 | below range | $17.99 | median price of its category |
| Home | 513112663 Farberware 4.7qt Stand Mixer Display | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 514775243 Mr Coffee 12c Coffee Maker Dis | $0.01 | below range | $44.99 | comparable item: Mr. Coffee Coffee Maker |
| Home | 515235324 Hamilton Beach Hb 2 Slice Digital Toaster Display | $0.01 | below range | $53.00 | comparable item: Hamilton Beach 2 Slice Modern Toaster with Digital |
| Home | 516652590 Presto Dehydrator Display | $0.01 | below range | $63.70 | comparable item: Presto Food Dehydrator |
| Home | 522111593 Mr Coffee Burmill Grndr Display | $0.01 | below range | $18.70 | median price of the same kind of item |
| Home | 523379248 Emerson 1.2 Mwo Display | $0.01 | below range | $7.49 | comparable item: Hamilton Beach Display Mwo |
| Home | 524765073 Hoover Onepwr Evolve Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 527183177 Delonghi Nespresso Vertuo Plus Black Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 528167796 Bissell Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 530795079 Beautiful White 6qt Slow Cooker NON-WORKING DISPLAY | $0.01 | below range | $34.97 | comparable item: Beautiful 4Qt Slow Cooker with Touch-Activated Dis |
| Home | 532525359 Hoover Display Hvr Steamscrub Mop Duwh20440 | $0.01 | below range | $45.55 | median price of the same kind of item |
| Home | 538456938 Mr Coffee Espresso Red Display | $0.01 | below range | $22.75 | median price of the same kind of item |
| Home | 539597757 Display Rowenta Ultimate DW80 Iron | $0.01 | below range | $1.00 | comparable item: New Display RW Ultimate Iron |
| Home | 539662127 Hamilton Beach Hb Flexbrew With Hot Water Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 543466274 Hamilton Beach Hb Glass Jar Blender Chrome Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 551119918 Magic Bullet Nutribullet 600 Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 551976003 Shark Sh Self Empty Rbt Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 553518204 Magic Bullet Nutribullet 900 Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 553652709 Jack Lalanne Power Air Fryer 360 Plus Dummy Display | $0.01 | below range | $79.00 | comparable item: Jack Lalanne 3.4 Quart Power Air Fryer |
| Home | 555083877 Presto Cooldaddy Df Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 558801688 Hamilton Beach Hb Double Breakfast Sandwich Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 559989410 Bissell Display | $0.01 | below range | $12.50 | comparable item: Display Basket |
| Home | 563065148 NV130 SPRING DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 571913674 Mr. Coffee 14-Cup Coffeemaker Display | $0.01 | below range | $39.87 | comparable item: Mr. Coffee 12-Cup Coffeemaker, 12 5/8"H x 11 13/16 |
| Home | 572239889 BISSELL CROSSWAVE CORDLESS NWD | $0.01 | below range | $1.00 | comparable item: BISSELL CROSSWAVE HF3 NWD |
| Home | 573009626 HART Stick Vacuum Display | $0.01 | below range | $22.57 | comparable item: BISSELL 3-in-1 Stick Vacuum |
| Home | 573362089 Hoover Dual Power Max Pet Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 575544875 Hamilton Beach Hb No Mess Waffle Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 575895840 Instant Pot 6qt Viva Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 576566929 HART 20V High Capacity Cordless Stick Vacuum NWD | $0.01 | below range | $51.47 | comparable item: Eureka Cordless 2-in-1 Stick Vacuum, 95A |
| Home | 578320804 Black & Decker B&d Rice Display | $0.01 | below range | $15.00 | comparable item: Black & Decker 16-Cup Rice Cooker |
| Home | 584065119 DSPIX140H | $0.01 | below range | $30.00 | median price of its category |
| Home | 584750517 Presto Digital Dehydrator Display | $0.01 | below range | $95.14 | comparable item: Presto Dehydro Digital Electric Food Dehydrator |
| Home | 586924809 Black & Decker Bd Easy Dial 12 Cup Coffee Maker Display | $0.01 | below range | $51.62 | comparable item: Black & Decker 8 Cup Black Easy Coffee Maker |
| Home | 589310242 Hamilton Beach Hb Bsm Display | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 590809559 Hamilton Beach Hb 1.1 Mwo | $0.01 | below range | $13.43 | comparable item: HB 1.1 MWO WSS DISPLAY |
| Home | 591043629 Dsp Shark Rocket Deluxe Pro Vac | $0.01 | below range | $30.00 | median price of its category |
| Home | 591311586 GOURMIA Grind & Brew Display | $0.01 | below range | $79.99 | comparable item: Gourmia Automatic Grind and Brew Coffee Maker |
| Home | 596102641 SAMSUNG DISPLAY Jet Cordless Stick Vacuum | $0.01 | below range | $51.47 | comparable item: Eureka Cordless 2-in-1 Stick Vacuum, 95A |
| Home | 596582271 Hoover Fusion Stick Vacuum Display | $0.01 | below range | $79.99 | comparable item: Hoover Flair Stick Vacuum With Powered N |
| Home | 601005642 Bissell Spotbot Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 601211825 Mr Coffee 12 Cup Switch Black Display | $0.01 | below range | $19.99 | comparable item: Mr. Coffee 12-Cup Switch Coffee Maker, Black |
| Home | 601779136 Oster Dfl Xl Toaster Oven Display | $0.01 | below range | $52.86 | comparable item: MS XL TOASTER OVEN |
| Home | 602108945 BI POWERLIFTER PET LIFT-OFF NWD | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 603229976 Shark Sh Vacmop Robot Nwd | $0.01 | below range | $7.98 | comparable item: Shark VACMOP |
| Home | 603369704 Hoover Floormate Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 605630155 Mr. Coffee 12cup Prg Coffee Maker Disply | $0.01 | below range | $19.36 | comparable item: Mr. Coffee 5 Cup Coffee Maker |
| Home | 606148914 Mr. Coffee® 12-Cup Programmable Coffee Maker with Strong Brew Selector | $0.01 | below range | $29.99 | comparable item: Mr. Coffee 12 Cup Programmable Coffee Maker with S |
| Home | 606207007 Instant Pot Duo80 Nwd | $0.01 | below range | $27.68 | median price of the same kind of item |
| Home | 606510215 HART Pro Upright Vacuum Display | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 609189821 Emerils Emeril Lagasse Pressurecooker8qt Display | $0.01 | below range | $48.26 | comparable item: Emeril Lagasse 2qt Tri-Ply Sauce Pan |
| Home | 610445488 Hamilton Beach Hb Panini Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 616571889 HART Hand Vacuum Display | $0.01 | below range | $18.18 | comparable item: HART 20V Hand Vacuum, HPHV01 |
| Home | 617087743 Mr Coffee Single Serve Brewer Display | $0.01 | below range | $99.85 | comparable item: Mr. Coffee 40 Ounce Single Serve Red Coffee Brewer |
| Home | 620416009 BISSELL ProHeat 2X Revolution Pet NWD | $0.01 | below range | $0.98 | comparable item: Pet Hair Eraser DualBrush NWD |
| Home | 621032650 Black+decker Smartech Robot Vac Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 622119494 Hoover Display Hvr Dual Power | $0.01 | below range | $30.00 | median price of its category |
| Home | 625723617 Ninja U Auto Iq Blender Display | $0.01 | below range | $89.00 | comparable item: Ninja Auto IQ Single Serve Blender |
| Home | 626914574 Mr. Coffee Mc 12cup Programmable Plexi Display | $0.01 | below range | $34.00 | comparable item: Mr. Coffee 12-cup Programmable Coffeemak |
| Home | 627944922 Dyson Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 627971275 Mr. Coffee 12-Cup Programmable Red Coffee Maker | $0.01 | below range | $67.48 | comparable item: Mr. Coffee 12 Cup Programmable Red Coffee Maker |
| Home | 632113508 Instant Pot Duo Mini 7-in-1 - Multi cooker - 3 qt - 700 W | $0.01 | below range | $50.00 | comparable item: Instant Pot DUO60 6 Qt 7-in-1 Multi-Use Programmab |
| Home | 639130485 Magic Bullet Display | $0.01 | below range | $7.49 | comparable item: Hamilton Beach Display Mwo |
| Home | 646516518 Black & Decker B+d 12sp Fusion Blade Ss Blender Display | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 647336827 Jack Lalanne Multi Cooker Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 650079908 Black & Decker Bd Airswivel Lite Display | $0.01 | below range | $40.12 | comparable item: Black & Decker B D Airswivel Lite |
| Home | 650118461 Instant Pot Duo60 Nwd | $0.01 | below range | $27.68 | median price of the same kind of item |
| Home | 650425794 Instant Pot Duo 3Qt Display | $0.01 | below range | $79.00 | comparable item: Instant Pot Duo 6qt Copper Ss |
| Home | 652732947 B 14C COFFEE DISPLAY | $0.01 | below range | $38.98 | comparable item: BonJour Coffee - 2 Pack |
| Home | 652893109 Bella Waffle Maker Display | $0.01 | below range | $29.99 | comparable item: Rotating Waffle Maker |
| Home | 654261866 Tineco Pure One S11 Spartan NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 654489696 Mr. Coffee 3-in-1 Frappe Frozen Coffeemaker Display | $0.01 | below range | $6.47 | median price of the same kind of item |
| Home | 655199002 Hamilton Beach Hb Glass Jar Blender Display Red | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 659136575 Hoover Elite Rewind Plus Display | $0.01 | below range | $20.61 | comparable item: Restored Hoover UH71200 Elite Rewind Plus Upright  |
| Home | 660302682 Mr Coffee 12c Speed Brew Red Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 661069550 Icoffee Davinci Coffee Maker Display | $0.01 | below range | $16.98 | median price of the same kind of item |
| Home | 661962116 Mr Coffee 12c Coffee Maker Bk Dis | $0.01 | below range | $44.99 | comparable item: Mr. Coffee Coffee Maker |
| Home | 664353479 Rowenta Rw Iron Perm Dsp | $0.01 | below range | $11.30 | median price of the same kind of item |
| Home | 677447185 Oster Classic Plus Blender Display | $0.01 | below range | $79.98 | comparable item: Classic 3-Speed Oster® Blender |
| Home | 684063061 Frigidaire Display Frig 1.4 Black Ss Mwo | $0.01 | below range | $46.80 | comparable item: MAINSTAYS 2.2 MWO BLACK DISPLAY |
| Home | 684727844 Ninja Steam Oven Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 684748961 Hamilton Beach Hb Xl Oven Display | $0.01 | below range | $49.53 | comparable item: Hamilton Beach Hb 6 Slice Toaster Oven |
| Home | 685147654 Bissell Bi Jetscrub Pet Nwd | $0.01 | below range | $0.98 | comparable item: Pet Hair Eraser DualBrush NWD |
| Home | 687323371 NutriBullet Juicer™ DISPLAY | $0.01 | below range | $9.87 | comparable item: Hangrees-The Juicer |
| Home | 687900534 Instant Pot PW Sweet Rose 6Qt Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 689004935 Hoover High Performance Swivel Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 692155838 Hoover Power Dash Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 693027577 Delonghi Nespresso Inissia Machine Black Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 695389683 Ninja Digital Touch Blender Display | $0.01 | below range | $34.88 | comparable item: Oster Digital Blender |
| Home | 695472515 Rival Griddle Display | $0.01 | below range | $18.96 | comparable item: Rival Griddle |
| Home | 699578594 Oster Blndr W/prtyjar D | $0.01 | below range | $17.99 | median price of its category |
| Home | 700608064 DSPBN700WMP DISPLAY | $0.01 | below range | $0.98 | comparable item: Display Crispi four qt, DSPFN100WMP |
| Home | 703414869 Oster Waffle Display | $0.01 | below range | $33.43 | comparable item: Oster DuraCeramic Waffle Maker |
| Home | 703840388 Cuisinart Food Processor Display | $0.01 | below range | $52.61 | comparable item: 8-Cup Food Processor |
| Home | 703985328 Mr Coffee 12c Red Coffee Maker Display | $0.01 | below range | $67.48 | comparable item: Mr. Coffee 12 Cup Programmable Red Coffee Maker |
| Home | 709594756 DSPCE250WMP Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 712981007 Instant Pot Pw 6qt Frontier Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 714448911 Mc 12c Programmable Coffee Display Red | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 720241847 Sodastream Exchange Upc | $0.01 | below range | $17.52 | median price of the same kind of item |
| Home | 720414144 Shark Comet 14 Inch Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 724390775 GF 2 SERVING DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 726600425 Hamilton Beach Toaster Display, Black | $0.01 | below range | $22.99 | comparable item: Hamilton Beach Smart Toast Toaster, Black, 22121 |
| Home | 726645200 Shark Sh Ion Robot Iq Display | $0.01 | below range | $64.94 | comparable item: Shark ION Robot® Series Replenishment Kit |
| Home | 733517050 Hamilton Beach Hb Food Processor Black Display | $0.01 | below range | $99.00 | comparable item: Hamilton Beach 70595 Food Processor |
| Home | 739255801 Ninja Kitchen Assistant Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 746298575 Power Xl Vortex Airfryer Plus 5qt Dummy | $0.01 | below range | $17.99 | median price of its category |
| Home | 750593948 BLACK+DECKER 3 Cup Rice Cooker Display | $0.01 | below range | $63.99 | comparable item: Cuckoo 12Cup Rice Cooker Display |
| Home | 755779412 Bunn Grx-b 10 Cup Coffee Brewer Display | $0.01 | below range | $24.96 | comparable item: 5 Cup Coffee Brewer - Red |
| Home | 756590299 Shark Display For Ultralite Power | $0.01 | below range | $30.00 | median price of its category |
| Home | 757735250 BEAUTIFUL TOASTER OVEN/AIR FRYER NON-WORKING DISPLAY | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 758171869 NJA CREAMI DISPLAY | $0.01 | below range | $0.98 | comparable item: Ninja Creami Display - XNC300BL |
| Home | 761251833 Shark Navigator Lift-away Vacuum Display | $0.01 | below range | $88.13 | comparable item: Refurbished Shark Navigator Lift-Away Upright Vacu |
| Home | 761692761 CUISINART Coffee Center™ Brew Basics DISPLAY, 64 Oz | $0.01 | below range | $18.70 | median price of the same kind of item |
| Home | 761814730 Oster Classic White Blender Display | $0.01 | below range | $39.00 | comparable item: Oster Classic 3-Speed Blender, Smoothie Blender, W |
| Home | 764213355 Dyson - V6 Slim Blue Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 765778584 Instant Pot Crisp Lite 6Qt Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 766993436 Dyson - Light Ball Animal Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 768238889 Ninja Auto Iq Master System Blender Disl | $0.01 | below range | $90.30 | comparable item: Refurbished Nutri Ninja Blender System with Auto-i |
| Home | 768385860 Mc 5cup Coffee Display Black | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 773453480 Black & Decker B&d 12c Coffeemaker Non-working Display | $0.01 | below range | $17.00 | comparable item: Black + Decker 12 Cup Coffeemaker |
| Home | 776114519 Mrc Steam Espresso Wmt Sled | $0.01 | below range | $17.99 | median price of its category |
| Home | 778211045 JC100 DISPLAY | $0.01 | below range | $17.99 | median price of its category |
| Home | 779423083 Hamilton Beach Hb Roaster Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 781850341 Shark Rotator Lift-away Duoclean Display | $0.01 | below range | $90.80 | comparable item: Shark® APEX™ DuoClean™ Powered Lift-Away®, AX950 |
| Home | 783660722 George Foreman 144 In Grill Display | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 789821799 Black + Decker Party Jar Blender Display | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 790628771 DISPLAY BLACK+DECKER POWERSERIES+ Cordless Stick Vacuum | $0.01 | below range | $99.99 | comparable item: BLACK+DECKER HFEK520J 3-N-1 Cordless Stick Vacuum |
| Home | 791076790 Black & Decker B&d 4 Slice Toaster Display | $0.01 | below range | $34.98 | comparable item: Black + Decker 2-Slice Toaster |
| Home | 791610928 DPLY SLED KEUR BRWR KEXPE BLK DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 794258215 Bissell Crosswave Pet Nwd | $0.01 | below range | $1.00 | comparable item: BISSELL CROSSWAVE HF3 NWD |
| Home | 796093691 Shark Ion Robot Display DSPRV754WM | $0.01 | below range | $64.94 | comparable item: Shark ION Robot® Series Replenishment Kit |
| Home | 799750639 Magic Bullet Nutribullet Veggie Bullet Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 801144022 Presto 20" Griddle Display | $0.01 | below range | $31.73 | comparable item: Presto 20" Electric Griddle |
| Home | 805201599 Shark Sh Navigator Deluxe Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 805655063 Hamilton Beach Hb Slow Cooker Display | $0.01 | below range | $27.66 | comparable item: Hamilton Beach 33147 Slow Cooker |
| Home | 805730342 Dyson Bll Ml Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 815633223 Shark Ion Robot with Ion Sabre Hand Vacuum | $0.01 | below range | $64.94 | comparable item: Shark ION Robot® Series Replenishment Kit |
| Home | 816075304 Hamilton Beach D14pl 1.1 Cu.ft. Digital | $0.01 | below range | $89.00 | comparable item: Hamilton Beach 1.3 Cu ft Digital Microwave Oven, B |
| Home | 816563750 Kitchenaid Culinary Center Dislay | $0.01 | below range | $17.99 | median price of its category |
| Home | 820088302 Dyson - Light Ball Mf Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 827738441 Keurig Kold White Drinkmaker Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 829691615 Bissell Proheat 2x Revolution Display Set | $0.01 | below range | $30.00 | median price of its category |
| Home | 832239743 Shark Sh Nav L-a Zerom Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 833777369 Cbella, Eramic Kettle Display | $0.01 | below range | $34.99 | median price of the same kind of item |
| Home | 834478551 Panasonic Mwo 2.2 Cft Display "nn-t945sfdisp" | $0.01 | below range | $17.99 | median price of its category |
| Home | 835410845 Oster 2slice Toaster Ss Display | $0.01 | below range | $34.99 | comparable item: Oster® 2-Slice Toaster |
| Home | 840383420 DSPIZ640HWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 841130993 BI PET STAIN ERASER POWERBRUSH NWD | $0.01 | below range | $6.49 | comparable item: BISSELL Pet Stain Eraser NWD |
| Home | 844152376 Bissell Bi-crosswave Cordless Max Nwd | $0.01 | below range | $21.99 | comparable item: BI CROSSWAVE CORDLESS MAX PET MULTI SURFACE BRUSH  |
| Home | 846127136 Dyson V6 Slm Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 847517216 Oster Stand Mixer Display | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 847526008 Oster Os Classic Blender W/food Process Rd Dis | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 849955814 Oster One Touch Blender Display | $0.01 | below range | $65.00 | comparable item: Oster 6 Cup One Touch Blender in Black |
| Home | 854312257 Galanz Ga 0.7 Retro Cream Mwo Dis | $0.01 | below range | $9.38 | comparable item: Galanz 1.2cf Airfry Mwo Dis |
| Home | 858435306 Ninja Foodi Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 861537068 Ninja Pro Ss Blender Display | $0.01 | below range | $79.08 | comparable item: Ninja Pro Single Serve Blender |
| Home | 864508667 GOURMIA THERMAL COFF DSP | $0.01 | below range | $17.99 | median price of its category |
| Home | 866632951 Bissell Powerlifter Pet Display | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 867694765 Shark Sh Lift Away Go Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 871643029 Instant Pot Ib Mini Af Display | $0.01 | below range | $27.68 | median price of the same kind of item |
| Home | 871740677 Powerxl Vortex Air Fryer Slimline 9qt Du | $0.01 | below range | $89.00 | comparable item: PowerXL Vortex Pro 8 Qt Air Fryer |
| Home | 872942573 Hoover Onepwr Blade Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 873123836 Shark Sh Vertex Crdls Nwd | $0.01 | below range | $30.00 | median price of its category |
| Home | 875521732 Mr. Coffee Burr Grinder Plexi Display | $0.01 | below range | $29.99 | comparable item: Mr. Coffee Coffee Grinder |
| Home | 875927096 Mr. Coffee Mc Hot Spot Station Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 876967778 Hoover Display Hvr High Pererforamnce Pet | $0.01 | below range | $30.00 | median price of its category |
| Home | 877883769 Mr Coffee 12 Cup Display | $0.01 | below range | $53.40 | comparable item: Green Mountain Coffee K-Cup Coffee |
| Home | 881796407 Shark Sh Lift-away Pro Display | $0.01 | below range | $59.99 | comparable item: Restored Shark Lift-Away Pro Steam Mop with Click  |
| Home | 882495430 Hamilton Beach 1.1 Cf/1000w Microwave | $0.01 | below range | $69.88 | comparable item: Hamilton Beach 0.9 Cf/900w Microwave |
| Home | 883072562 Oster Dfl 4slice Toaster Display | $0.01 | below range | $34.99 | comparable item: Oster® 2-Slice Toaster |
| Home | 886324009 Mainstays 0.7 Cu. Ft. 700W Microwave Oven | $0.01 | below range | $56.98 | comparable item: Mainstays 0.7 cu ft 700W Microwave Oven |
| Home | 890407061 Oster 14sp Blender B Dis | $0.01 | below range | $23.61 | comparable item: Oster 2607 Hand Blender |
| Home | 893675224 Bissell Powerforce Compact Display | $0.01 | below range | $36.52 | comparable item: POWERFORCE COMPACT |
| Home | 894099047 Hoover Hv Air Steerable Disp | $0.01 | below range | $99.00 | comparable item: Hoover WindTunnel 3 Air Steerable |
| Home | 897267537 Ninja Duo Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 900677511 Dirt Devil Power Stick Disp | $0.01 | below range | $43.10 | comparable item: Dirt Devil Power Stick Vacuum, M084100RED |
| Home | 901127796 Shark Sh Wandvac Go Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 901232173 Rival 4 Slice Toaster Oven Display | $0.01 | below range | $25.16 | comparable item: Rival 4 Slice Toaster Oven |
| Home | 906080710 SS150 BLENDER DISPLAY | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 909231532 Presto Tilt Griddle Display | $0.01 | below range | $31.73 | comparable item: Presto 20" Electric Griddle |
| Home | 909397398 Oster Dfl 6slice Toaster Oven Display | $0.01 | below range | $69.88 | comparable item: Oster 6 Slice Toaster Oven (6293) - Electric oven |
| Home | 910195803 Oster Os 7cup Blender Display | $0.01 | below range | $99.99 | comparable item: Oster 6 Cup Table Top Blender |
| Home | 912213772 Services Disaply Unit For Hb Pod Coffee Maker | $0.01 | below range | $37.84 | median price of the same kind of item |
| Home | 913622492 Bissell Bi Powerlifter Superlight Disp | $0.01 | below range | $30.00 | median price of its category |
| Home | 916635224 Shark Rotator Lift Away Professional Display | $0.01 | below range | $42.49 | comparable item: Shark NV510 Rotator Professional Lift Away Upright |
| Home | 916943374 Display HB Sandwich Maker | $0.01 | below range | $20.49 | comparable item: Rival Sandwich Maker |
| Home | 922125550 Powerxl Air Fryer Grill Plus Dummy Displ | $0.01 | below range | $89.99 | comparable item: 5QT 6-IN-1 AIR FRYER |
| Home | 924436876 Bissell Bolt Ext Pet Nwd | $0.01 | below range | $0.98 | comparable item: Pet Hair Eraser DualBrush NWD |
| Home | 926191047 Bissell Powerforce Powerbrush Disp Unit | $0.01 | below range | $30.00 | median price of its category |
| Home | 927029841 Oster DiamondForce Waffle maker Display | $0.01 | below range | $67.48 | comparable item: Oster® DiamondForce™ Nonstick Flip Waffle Maker |
| Home | 927647612 Shark Sh Rotr L-a Dc Zerom Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 931115683 Hamilton Beach Easy Clean Juice Display | $0.01 | below range | $28.16 | median price of the same kind of item |
| Home | 932620090 Ninja Blender Iq Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 934463011 Shark Display Rocket Dlx Vacuum | $0.01 | below range | $49.38 | comparable item: Refurbished Shark Rocket Powerhead Vacuum |
| Home | 934585243 Oster French Door Oven With Air Fryer Display | $0.01 | below range | $100.00 | comparable item: Oster® Compact Countertop Oven With Air Fryer, Sta |
| Home | 938447962 GF 144IN SS GRILL DISPLAY | $0.01 | below range | $54.88 | comparable item: BLACK+DECKER 144" Grill |
| Home | 938562645 Mainstays Personal Blender Display | $0.01 | below range | $15.13 | comparable item: Mainstays Personal Blender |
| Home | 938769435 DSPIG600P | $0.01 | below range | $17.99 | median price of its category |
| Home | 939511946 George Foreman Gf Gr2144p Non-working Display Sample | $0.01 | below range | $19.88 | median price of its category |
| Home | 947691419 Kitchenaid 12cup Coffeemaker Display | $0.01 | below range | $69.98 | comparable item: Better Chef 10-50 Cup Coffeemaker |
| Home | 947917117 Hamilton Beach Disply | $0.01 | below range | $17.99 | median price of its category |
| Home | 947943283 George Foreman Gf 84 In Multi-plate Grill Display | $0.01 | below range | $44.00 | comparable item: George Foreman 4 Serving Classic Plate Grill |
| Home | 948516969 Bissell Bissel Proheat Pet Advanced Display | $0.01 | below range | $19.92 | comparable item: BISSELL Advanced Pet Urine Eliminator, 50 oz. |
| Home | 949366307 Irobot Braava 245 Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 950931894 Bissell Powerforce Helix Nwd | $0.01 | below range | $54.00 | comparable item: Bissell Powerforce Helix-berry |
| Home | 952677741 Bissell Pet Stain Eraser Nwd | $0.01 | below range | $6.88 | median price of the same kind of item |
| Home | 954081285 Keurig K-duo Brewer Display | $0.01 | below range | $13.49 | comparable item: K-Duo™ Brewer 3 Month Care Kit |
| Home | 954759336 Ninja Single Serve Coffee Maker | $0.01 | below range | $64.20 | comparable item: Salton 2-in-1 Single Serve Coffee Maker |
| Home | 955636486 Cuisinart Coffeemaker Display | $0.01 | below range | $76.49 | comparable item: Cuisinart 14 Cup Programmable Coffeemaker |
| Home | 956943485 Bissell Bi Pf Helix Turbo Nwd | $0.01 | below range | $91.00 | comparable item: Bissell Bi Powerforce Helix Turbo Rewind Nwd |
| Home | 956963972 Emeril Lagasse Power Grill 360 Plus Dummy Display | $0.01 | below range | $29.96 | comparable item: Shaq Power Grill Plus - 4 Serving |
| Home | 957237341 OS BLDNR RED DSPLY | $0.01 | below range | $17.99 | median price of its category |
| Home | 957791312 Instant Brands 10l Air Fry Oven Display | $0.01 | below range | $2.73 | comparable item: MS 0.9 Air Fry Display |
| Home | 958256127 Instant Pot Vortex 10Qt Display | $0.01 | below range | $14.50 | comparable item: Essentials 6Qt 3-in-1 Multi Cooker Display |
| Home | 960085141 Ninja Coffee Brewer Display | $0.01 | below range | $69.30 | comparable item: Refurbished Ninja Coffee Brewer with Auto-iQ, CF02 |
| Home | 960338423 Farberware Royalty Deep Fryer Disp | $0.01 | below range | $1.80 | comparable item: Farberware Royalty Farberware Deep Fryer Display |
| Home | 962833888 Shark Rocket Stick Display | $0.01 | below range | $64.00 | comparable item: Refurbished Shark Rocket Ultra-Light Corded Stick  |
| Home | 966528507 KitchenAid Food Processor Display | $0.01 | below range | $99.99 | comparable item: KitchenAid KFP715 Food Processor |
| Home | 967871257 Dyson - Upright Vacuum | $0.01 | below range | $49.94 | comparable item: Eureka Powerspeed Upright Vacuum |
| Home | 969421423 Irobot Category Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 970155841 George Foreman Gf 100 In Ceramic Grill Display | $0.01 | below range | $39.11 | comparable item: George Foreman 80'' Grill |
| Home | 970790240 Mr Coffee Espresso Dis | $0.01 | below range | $58.98 | comparable item: BonJour Espresso - 2 Pack |
| Home | 971818822 Ninja Foodi Flip Oven Display | $0.01 | below range | $99.99 | comparable item: Ninja® Foodi™ 2-in-1 Flip Toaster, 2-Slice Toaster |
| Home | 973119853 Shark Sh Ionsabre Hand Vac Display | $0.01 | below range | $57.00 | comparable item: Shark VX33 18V Bagless Hand Vac |
| Home | 973821585 iFloor 2 NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 975640322 Mr. Coffee 12-Cup Switch White Coffee Maker | $0.01 | below range | $24.99 | comparable item: Mr. Coffee 5-Cup White Switch Coffee Maker 2134286 |
| Home | 977639030 Shark Navigator® Lift-Away® XL Upright Vacuum DISPLAY | $0.01 | below range | $88.13 | comparable item: Refurbished Shark Navigator Lift-Away Upright Vacu |
| Home | 980807607 Shark Fuse Lift Away Corded Display | $0.01 | below range | $97.63 | comparable item: Shark Apex UpLight with Lift-Away DuoClean Corded  |
| Home | 981230282 Mr. Coffee Mc Mini Brewer Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 982536975 Power Xl Pxl Microwave Af Oven Dummy | $0.01 | below range | $48.65 | median price of the same kind of item |
| Home | 983709814 Hamilton Beach Hb Flexcook Slow Cooker Display | $0.01 | below range | $27.66 | comparable item: Hamilton Beach 33147 Slow Cooker |
| Home | 985199426 Hamilton Beach D14pl 1.1 Cf/1000w Microwave | $0.01 | below range | $77.86 | comparable item: Hamilton Beach D14pl 1.1cf/1000w Microwave |
| Home | 985494811 B 7SP BLENDER DISPLY | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 986438465 Powerxl Smokeless Grill Display | $0.01 | below range | $64.95 | comparable item: CRUX CRX14726 Smokeless Grill 12" x 16" |
| Home | 987888777 Mc Switch Coffee Display Black | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 990551497 Oster 14sp Blender W Dis | $0.01 | below range | $23.61 | comparable item: Oster 2607 Hand Blender |
| Home | 992734497 Cuisinart Toaster Oven Display | $0.01 | below range | $86.80 | comparable item: Cuisinart Convection Toaster Oven |
| Home | 994735908 GOURMIA HOT/ICE DS | $0.01 | below range | $17.99 | median price of its category |
| Home | 997624385 Black & Decker 12-Cup Programmable Coffee Maker | $0.01 | below range | $37.53 | comparable item: Black & Decker 12 Cup Programmable Coffee Maker |
| Home | 999691009 BISSELL POWERFORCE POWERBRUSH PET XL NWD | $0.01 | below range | $0.98 | comparable item: Pet Hair Eraser DualBrush NWD |
| Home | 1026447960 magic bullet Mini Juicer DISPLAY -w/o Cup | $0.01 | below range | $59.99 | comparable item: Magic Bullet Mini Juicer with Cup |
| Home | 1060056464 DSPWD100WMP Display | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 1066875094 1500W 9x15 SMOKELESS GRILL WITH PYRAMID STYLE PLATES & SS DECORATION - | $0.01 | below range | $35.93 | median price of the same kind of item |
| Home | 1084838419 BISSELL Revolution HydroSteam NWD, 3434 | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 1090264287 Display 12" Electric Skillet | $0.01 | below range | $69.98 | comparable item: Presto 7300 Electric Skillet |
| Home | 1111743608 DSPAZ3000WMP Display | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 1151954419 DSPHZ3000WMP Display | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 1163501568 Shark Cordless Stick Vacuum DISPLAY | $0.01 | below range | $51.47 | comparable item: Eureka Cordless 2-in-1 Stick Vacuum, 95A |
| Home | 1199032162 iHome Juno Non-Working Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 1209104477 DSPSE460WMP Display | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 1268102806 BISSELL PowerForce Rewind Pet NWD, 3333W | $0.01 | below range | $91.00 | comparable item: Bissell Bi Powerforce Helix Turbo Rewind Nwd |
| Home | 1272002069 Beautiful 5.3QT Stand Mixer White Non-Working Display | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 1275448348 BISSELL PowerForce Helix NWD, 3313W | $0.01 | below range | $54.00 | comparable item: Bissell Powerforce Helix-berry |
| Home | 1277813853 Crockpot 8Qt Slow Cooker Rhubarb Display | $0.01 | below range | $22.37 | comparable item: Crockpot 4.5 qt Slow Cooker SCR450-S |
| Home | 1279780695 SS-15P1WMDIS Display | $0.01 | below range | $13.43 | comparable item: Hamilton Beach 1.1 MWO SS DISPLAY |
| Home | 1292598748 BISSELL 3-in-1 & Powerlifter ION NWD 3711W | $0.01 | below range | $85.53 | comparable item: PowerLifter Pet |
| Home | 1383379322 Oster Classic White Blender Display | $0.01 | below range | $39.00 | comparable item: Oster Classic 3-Speed Blender, Smoothie Blender, W |
| Home | 1396523365 Cuisinart 14 Cup Coffee Maker Display, DCC-3200P1WMDIS | $0.01 | below range | $48.00 | comparable item: 12-Cup Coffee Maker |
| Home | 1413341736 Instant Pot RIO Chef 8QT Pressure Cooker - NWD | $0.01 | below range | $79.71 | comparable item: Instant Pot Superior Cooker Chef Series 7.5Qt Slow |
| Home | 1447877686 DPLY DEMO KEU BRWR MINIP EVNG TEAL SHELL | $0.01 | below range | $17.99 | median price of its category |
| Home | 1497448827 Rise By Dash 7" Waffle Maker Displayer | $0.01 | below range | $36.75 | comparable item: Nesco Waffle Maker |
| Home | 1502109190 DSPNC100WMP NINJA DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 1536230879 Hoover SMARTWASH ESSENTIALS DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 1573377311 HART 20V BIN STICK NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 1585232376 NINJA SIZZ GRILL Display | $0.01 | below range | $35.93 | median price of the same kind of item |
| Home | 1588281586 Hamilton Beach 2 Slice Toaster NWD | $0.01 | below range | $72.54 | comparable item: Hamilton Beach Professional 2 Slice Toaster 22990 |
| Home | 1595154687 BISSELL PowerForce Turbo Pet NWD, 3332W | $0.01 | below range | $58.33 | comparable item: Bissell Powerforce Turbo |
| Home | 1627508534 DD MS Reach DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 1638301730 Crockpot 7QT Slow Cooker Grey Display | $0.01 | below range | $22.37 | comparable item: Crockpot 4.5 qt Slow Cooker SCR450-S |
| Home | 1700626825 DD Power Max DISPLAY | $0.01 | below range | $13.00 | comparable item: Dirt Devil Power Max Bagless Upright Vacuum, UD701 |
| Home | 1739629375 DSPWS640WM Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 1757448981 SHARK RV2300 8FT POD DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 1827449703 Chefman 4 Slice Panini Press Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 1857958061 DSPNV250WMP Vacuum Display | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 1904399446 ENV150B Nespresso Vertuo Omni Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 1917003389 (Nova S1 Pro/iHRVS1PRO) 8ft POD | $0.01 | below range | $30.00 | median price of its category |
| Home | 1938135893 Rise By Dash Clear View 2-Slice Toaster Displayer | $0.01 | below range | $52.00 | comparable item: Rise by Dash Clear View Window 2-Slice Toaster Blu |
| Home | 1976944010 Mr Coffee 12 Cup Rapid Brew EHX Omni Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 1979872325 eufy LR20 Display for LR20 | $0.01 | below range | $30.00 | median price of its category |
| Home | 1996067928 Instant Vortex 6QT Slim Air Fryer - NWD | $0.01 | below range | $88.58 | comparable item: PowerXL Vortex Pro 6 Qt Air Fryer |
| Home | 2067868586 Shark Carpet Extractor EX200 DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2074708789 Hoover WindTunnel w/ Tanglegaurd DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2089956551 Shark Rotator Pet Upright Vacuum DISPLAY | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 2105708778 DD Multisurface DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2105810666 SHARK ROBOT RV2400WDWM DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2137803752 Ninja Thirsti Shelf Display DSPWC1000WM | $0.01 | below range | $22.52 | median price of its category |
| Home | 2142000501 Instant Pot RIO Chef 6QT Pressure Cooker - NWD | $0.01 | below range | $79.71 | comparable item: Instant Pot Superior Cooker Chef Series 7.5Qt Slow |
| Home | 2183861281 Espresso DSP | $0.01 | below range | $58.98 | comparable item: BonJour Espresso - 2 Pack |
| Home | 2190415228 DSPRV2300SWMP DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2199297081 SV1114 WM DISPLAY WMT | $0.01 | below range | $30.00 | median price of its category |
| Home | 2208544211 DPLY SLED KEUR BRWR KICDE GRAY WMT DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 2262419361 Hoover 20v Cleanslate DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2294348698 Shark Upright Vac with Powerfins DISPLAY | $0.01 | below range | $13.18 | comparable item: Mainstays Upright Display |
| Home | 2304947378 Ninja Blend Sense Duo Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 2337019546 Hoover WindTunnel w/ Tangleguard DISPLAY DUUH77110WM | $0.01 | below range | $30.00 | median price of its category |
| Home | 2436874212 Wyze Robot Vacuum Display | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 2445195390 DSPDCT400WMP NINJA OVEN MULTI Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 2445460492 POWER 6QT AIRFRY NWD | $0.01 | below range | $89.99 | comparable item: 5QT 6-IN-1 AIR FRYER |
| Home | 2451558441 XRV2400WD SHARK RV2400WD 8FT POD | $0.01 | below range | $30.00 | median price of its category |
| Home | 2462413329 Bartesian Duet Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 2466788573 Gourmia 4C Multi-Function 5-Bar Espresso Machine DISPLAY | $0.01 | below range | $64.69 | comparable item: Gourmia Espresso 15-Bar, 4-Cup Stainless Steel Aut |
| Home | 2483629378 DD MS Pet DISPLAY | $0.01 | below range | $58.90 | comparable item: DD EXPRESS COMPACT + Pet Powder |
| Home | 2497394268 Shark Rotator Pet Lift-Away ADV DISPLAY, DSPLA700WMP | $0.01 | below range | $71.34 | comparable item: Shark Rotator Lift-Away ADV Upright Vacuum, Pet Fr |
| Home | 2509771719 Shark Robot Display DSPRV2400WSWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 2538454899 BISSELL PowerLifter Turbo Stick Vacuum NWD | $0.01 | below range | $23.44 | comparable item: BISSELL 3-in-1 Stick Vacuum 2030B |
| Home | 2631829102 SHARK DSP DSPRV2300WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 2650520454 HB BLENDER RED NWD | $0.01 | below range | $44.99 | comparable item: Hamilton Beach 53206HB 2-Speed Blender |
| Home | 2669354757 Instant Pot 7.5QT Slow Cooker - NWD | $0.01 | below range | $79.71 | comparable item: Instant Pot Superior Cooker Chef Series 7.5Qt Slow |
| Home | 2706562802 Mr. Coffee Speed Brew Stainless Steel Display | $0.01 | below range | $25.45 | median price of the same kind of item |
| Home | 2716756660 ENV90B POP PP WLMT DISPLAY | $0.01 | below range | $17.88 | median price of the same kind of item |
| Home | 2723304214 NINJA OVEN MULTI Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 2761233281 Wyze Cordless Vacuum S Display | $0.01 | below range | $99.98 | comparable item: Wyze S2 Cordless Anti-Tangle Vacuum |
| Home | 2767298310 Little Green HydroSteam NWD | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 2779259893 HOOVER STREAMLINE DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2802592951 DSPHZ700WMP WALMART DISPLAY | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 2847471387 Inspirex Toaster NWD | $0.01 | below range | $23.52 | comparable item: Proctor Silex 22335 Toaster |
| Home | 2872617118 BlendJet2 Shelf Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 2875494657 GOURM 4QT AIRFRY NWD | $0.01 | below range | $52.90 | comparable item: Gourmia 2.2QT White |
| Home | 2906248354 Shark StainStrike PX200 DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 2977145378 PowerXL Smokeless Grill Elite Plus Non-Working Display | $0.01 | below range | $35.93 | median price of the same kind of item |
| Home | 2998961333 eufy 25C Robovac Wall Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 3003798298 HB BLENDER BLACK NWD | $0.01 | below range | $50.95 | comparable item: Hamilton Beach 700 W 40 oz Blender, Black |
| Home | 3078824710 NINJA 10Q AIRFRY Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 3118274246 eufy G30 Robovac Wall Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 3169663737 NINJA 10Q AIRFRY Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 3388263305 Shark Carpet Extractor EX150 DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 3415147021 SH RV2400WSWD 8FT POD | $0.01 | below range | $30.00 | median price of its category |
| Home | 3574568064 Oster One Touch Blender Display | $0.01 | below range | $65.00 | comparable item: Oster 6 Cup One Touch Blender in Black |
| Home | 3683012134 NINJA 7Q AIRFRY Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 3684733178 eufy L50 Display Wall Display | $0.01 | below range | $81.46 | comparable item: CEP, Wall Display Rack, 1 Each, White |
| Home | 3721794520 Display Kitchen Kettle | $0.01 | below range | $38.37 | comparable item: Presto Kitchen Kettle Multi-Cooker |
| Home | 3737540451 Mr Coffee 14 Cup Stainlees Steel Omni Display | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 3789995088 Pet Hair Eraser Slim Corded NWD | $0.01 | below range | $0.98 | comparable item: Pet Hair Eraser DualBrush NWD |
| Home | 3791655549 Shark Cordless Stick Vacuum AE DISPLAY | $0.01 | below range | $51.47 | comparable item: Eureka Cordless 2-in-1 Stick Vacuum, 95A |
| Home | 3797039266 eufy L50+ Wall Display | $0.01 | below range | $81.46 | comparable item: CEP, Wall Display Rack, 1 Each, White |
| Home | 3825676120 HV Wind Tunnel All Terrain DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 3855622259 HB FOOD PROCESSOR NWD | $0.01 | below range | $99.00 | comparable item: Hamilton Beach 70595 Food Processor |
| Home | 3878197120 Oster Classic Black Blender Display | $0.01 | below range | $33.69 | comparable item: Oster Classic 3-Speed Blender, Smoothie Blender, B |
| Home | 3942656929 Ninja XL Processor DISPLAY | $0.01 | below range | $23.99 | comparable item: Ninja Professional XL Food Processor-Storage Box |
| Home | 3965648399 DD REWIND DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 3970201516 (Nova S1/iHRVS1-) 8ft POD | $0.01 | below range | $30.00 | median price of its category |
| Home | 3978414164 8FT ROBOT SHARK VACMOP ROBOT RV2300S Dummy | $0.01 | below range | $30.00 | median price of its category |
| Home | 5077879251 CHEFMAN 4-SLICE BELGIAN WAFFLE MAKER DISPLAY | $0.01 | below range | $74.95 | comparable item: Cuisinart 4-Slice Belgian Waffle Maker, Square |
| Home | 5089154478 Black Terra Machine Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 5102884322 Beautiful Perfect Grind Programmable Single Serve Coffee Maker, White  | $0.01 | below range | $79.00 | comparable item: Beautiful by Drew Barrymore Perfect Grind Programm |
| Home | 5106891258 HAMILTON BEACH LONG SLOT TOASTER DISPLAY | $0.01 | below range | $60.00 | comparable item: Hamilton Beach Long Slot Keep Warm Toaster, Model  |
| Home | 5106941727 Hamilton Beach Defrost Slow Cooker Display | $0.01 | below range | $27.66 | comparable item: Hamilton Beach 33147 Slow Cooker |
| Home | 5113183793 HB 12C COFFEE DISPLAY | $0.01 | below range | $68.00 | comparable item: HB TRIO COFFEE MAKER |
| Home | 5113233429 Ninja Grand Kitchen System 1200 DISPLAY, DSPKS500WMP | $0.01 | below range | $17.99 | median price of its category |
| Home | 5113283028 Beautiful 5.3qt Stand Mixer, Lavender by Drew Barrymore, NON-WORKING D | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 5126097429 DSPIZ240WMP Cordless Vacuum Display | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 5126097591 HV CLEANSLATE XL NWD DUFH15010VWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 5129878895 Hamilton Beach Artisan Dough & Bread Maker Display, 29985DISW | $0.01 | below range | $7.83 | median price of the same kind of item |
| Home | 5129928169 Beautiful Rotating Waffle Maker, White Icing by Drew Barrymore, NON-WO | $0.01 | below range | $34.98 | comparable item: Beautiful Rotating Belgian Waffle Maker, White Ici |
| Home | 5129928402 DD Carpet Washer Display DUFD50310WM | $0.01 | below range | $20.84 | median price of its category |
| Home | 5129928454 eufy G50 Wedge Display | $0.01 | below range | $51.06 | comparable item: THE WEDGE ThermaSeat |
| Home | 5129928597 DSPIZ560HWMP Vacuum Display | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 5130059950 BARTESIAN COCKTAIL MACHINE DISPLAY | $0.01 | below range | $17.99 | median price of its category |
| Home | 5137123968 HAMILTON BEACH SMOOTHIE BLENDER, WHITE, DISPLAY (50181FDISW) | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 5137123969 Hamilton Beach Single Serve Blender Display (51190FDISW) | $0.01 | below range | $14.88 | comparable item: Hamilton Beach Single-Serve Blender |
| Home | 5137969781 Hamilton Beach Smoothie Smart Blender, 48 Oz. Glass Jar, Display, (562 | $0.01 | below range | $49.88 | comparable item: Hamilton Beach Smoothie Smart Blender, 48 Oz. Glas |
| Home | 5138506547 HB 5C COFFEE DISPLAY | $0.01 | below range | $68.00 | comparable item: HB TRIO COFFEE MAKER |
| Home | 5150283323 Hamilton Beach FlexBrew Advanced 5-in-1 Coffee Maker Display WESTROCK  | $0.01 | below range | $93.26 | comparable item: Hamilton Beach FlexBrew Trio Coffee Maker, 56 fl o |
| Home | 5152138474 BLACK+DECKER 4-Slice Toaster with Extra-Wide Slots, Black/Silver, Non- | $0.01 | below range | $27.48 | comparable item: BLACK+DECKER 2-Slice Extra Wide Slot Toaster, Blac |
| Home | 5152138475 BLACK+DECKER 2-Slice Toaster with Extra Wide Slots, Black/Silver, Non- | $0.01 | below range | $27.48 | comparable item: BLACK+DECKER 2-Slice Extra Wide Slot Toaster, Blac |
| Home | 5152138629 BLACK+DECKER Rapid Toast 2-Slice Toaster, Black Stainless Steel, Non-W | $0.01 | below range | $58.44 | comparable item: BLACK+DECKER TR3500SD Rapid Toast 2-Slice Toaster, |
| Home | 5152188071 Black + Decker Pearl Glide Steam Iron with Pearl-Infused Ceramic Solep | $0.01 | below range | $81.84 | comparable item: (2 pack) (2 pack) BLACK+DECKER Pearl Glide Steam I |
| Home | 5152188073 i3 Travel Steam Iron - Non Working Display | $0.01 | below range | $31.16 | comparable item: (2 pack) (2 pack) Steamfast SF-707 Mighty Steam Ir |
| Home | 5152509117 Hamilton Beach Air Fry Toaster Oven Display | $0.01 | below range | $84.22 | comparable item: GreenLife Air Fry Toaster Oven | Turquoise |
| Home | 5164703666 DSPHV200WMP Corded Vac Display | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 5164703680 IONVAC LIDAR 4FT POD NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 5164703915 DD Cordless Stick NWD DUBD57010V | $0.01 | below range | $30.00 | median price of its category |
| Home | 5164753121 CUISIN AirFryer TOA 70 NWD | $0.01 | below range | $17.99 | median price of its category |
| Home | 5166665877 DSPRV2300AEWMP Robot Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 5166715091 DSPBU3120WMP Cordless Stick Vacuum Display | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 5166715094 (Nova S1 Pro/iHRVS1PRO) 4ft POD | $0.01 | below range | $30.00 | median price of its category |
| Home | 5166715113 HV ONEPWR Emerge NWD DUBH53610VWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 5166715322 CUISIN 2STOST SS NWD | $0.01 | below range | $17.99 | median price of its category |
| Home | 5169277018 MS 0.7 CF White DISpla | $0.01 | below range | $20.60 | comparable item: MS 1.1 CF DISPLAY |
| Home | 5171696131 Beautiful Countertop Microwave Oven, 1 cu ft, White, Model BFCMS811WES | $0.01 | below range | $53.78 | comparable item: Rival 0.7 cu ft Countertop Microwave Oven in White |
| Home | 5175790168 DPLY SHELL KEUR BRWR KEXPE PACIFIC BLUE DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 5193278355 Beautiful Espresso Machine, White Icing, WR NON-WORKING DISPLAY | $0.01 | below range | $48.47 | median price of the same kind of item |
| Home | 5195244199 Chefman RJ11 Pop Display | $0.01 | below range | $12.62 | median price of the same kind of item |
| Home | 5195244334 Beautiful Perfect-Grind Single Serve Coffee Maker, White Icing, WR NON | $0.01 | below range | $79.00 | comparable item: Beautiful by Drew Barrymore Perfect Grind Programm |
| Home | 5195359842 DISPLPAY UNIT FOR - 1.5 cu. ft. Countertop Microwave with Smart Invert | $0.01 | below range | $48.65 | median price of the same kind of item |
| Home | 5200191335 DPLY SLED KEU BRWR KEXPE PACIFIC BLU WMT DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 5201411231 HB 0.9 CF SS DISPLAY | $0.01 | below range | $7.79 | comparable item: HB 0.9 CF SS MWO DIS |
| Home | 5201867973 GA 0.9 AIRFRY DISPLAY | $0.01 | below range | $17.99 | median price of its category |
| Home | 5202255728 GA 0.7 RETRO BLU DIS | $0.01 | below range | $17.99 | median price of its category |
| Home | 5202515284 Hamilton Beach Countertop Microwave Oven, 1 cu ft, 700 W, Gray | $0.01 | below range | $55.89 | comparable item: Hamilton Beach 0.7 cu ft Countertop Microwave Oven |
| Home | 5207222838 Display Nespresso VertuoPOP Dark Gray Coffee and Espresso | $0.01 | below range | $84.97 | comparable item: Nespresso VertuoPOP Dark Gray Coffee and Espresso  |
| Home | 5212441985 Chefman RJ38-SQSS-5T2P POP Display | $0.01 | below range | $12.62 | median price of the same kind of item |
| Home | 5212491671 MR. COFFEE 12 CUP SPEEDBREW OMNI DISPLAY | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 5212491672 MR. COFFEE 12CUP PROG WOOD DISPLAY | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 5212491673 MR. COFFEE SWITCH WOOD DISPLAY | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 5212491674 MR. COFFEE 5 CUP WOOD DISPLAY | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 5212541531 Beautiful 14-Cup Programmable Drip Coffee Maker, White Icing, WR NON-W | $0.01 | below range | $69.00 | comparable item: Beautiful by Drew Barrymore 14-Cup Programmable Dr |
| Home | 5212541797 Mr Coffee Brand Signage | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 5212541983 George Foreman 2 Serving Contact Grill Display GR012F-1AGWDIS | $0.01 | below range | $32.98 | comparable item: George Foreman 2-Serving Classic Plate Grill , Bla |
| Home | 5212591274 Gourmia 4C Espresso WestRock Display | $0.01 | below range | $22.75 | median price of the same kind of item |
| Home | 5212591405 XCLBOXCGWM Corrugated Box Comparison DSP | $0.01 | below range | $30.00 | median price of its category |
| Home | 5212591507 nutribullet Pro Display - Matte Black | $0.01 | below range | $95.09 | comparable item: nutribullet Pro 32 oz. 900 Watt Personal Blender,  |
| Home | 5212591647 MR. COFFEE FRAPPE WOOD DISPLAY | $0.01 | below range | $17.66 | median price of the same kind of item |
| Home | 5218232175 DPLY DEMO KEUR BRWR KICDE GRAY SHELL | $0.01 | below range | $30.00 | median price of its category |
| Home | 5219476297 DPLY DEMO KEUR BRWR KEXPE BLK SHELL | $0.01 | below range | $30.00 | median price of its category |
| Home | 5222350385 DPLY SHELL KEUR BRWR KDUOE GEN2 DISPLAY | $0.01 | below range | $0.98 | comparable item: DPLY SLED KEUR BRWR K-ELITE DISPLAY |
| Home | 5226729105 DPLY DEMO KEUR BRWR KSLM BLK SHELL | $0.01 | below range | $30.00 | median price of its category |
| Home | 5226743375 Mainstays Single Serve Coffee Maker - NON-WORKING DISPLAY | $0.01 | below range | $64.20 | comparable item: Salton 2-in-1 Single Serve Coffee Maker |
| Home | 5229769719 Display Presto Ceramic Griddle/Warmer | $0.01 | below range | $45.87 | comparable item: Presto Ceramic Nonstick Electric Griddle/Warmer Pl |
| Home | 5229819274 Chefman Barista Pro Espresso Machine - Black POP Display | $0.01 | below range | $48.47 | median price of the same kind of item |
| Home | 5230946313 DPLY DEMO KEUR BRWR KELIT BRSH SLTE SHELL | $0.01 | below range | $30.00 | median price of its category |
| Home | 5232316310 Chefman Barista Pro Espresso Machine - Black POP Westrock Display | $0.01 | below range | $48.47 | median price of the same kind of item |
| Home | 5258440303 Cuisinart 12 Cup Coffee Maker Display, DCC-1220BKSDIS | $0.01 | below range | $48.00 | comparable item: 12-Cup Coffee Maker |
| Home | 5258440304 Cuisinart 14 Cup Coffee Maker Display, DCC-3200WMDIS | $0.01 | below range | $48.00 | comparable item: 12-Cup Coffee Maker |
| Home | 5258490260 CUISIN Air Fryer TOV-70 NWD | $0.01 | below range | $10.10 | comparable item: Mainstays Air Fryer Nwd |
| Home | 5258490290 CUISIN 2STOST SS NWD | $0.01 | below range | $17.99 | median price of its category |
| Home | 5262667294 ENV120BG OMNI Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 5262667435 AIR FRYER DUAL DSP, DSPSL400WMP | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 5262667436 AIR FRYER DSP, DSPAF180WMP | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 5262667755 Ultima Cosa Semi Automatic Espresso Machine Display with Wooden Base | $0.01 | below range | $48.47 | median price of the same kind of item |
| Home | 5262667780 COFFEE MAKER DSP, XCE250 | $0.01 | below range | $53.65 | comparable item: Hamilton Beach 44559 Coffee Maker |
| Home | 5265004999 COFFEE MAKER DSP, XCFP300WM | $0.01 | below range | $37.84 | median price of the same kind of item |
| Home | 5265054000 COFFEE MAKER DSP, XCM300WM | $0.01 | below range | $37.84 | median price of the same kind of item |
| Home | 5265054199 Nespresso Pop Blk WR Wood Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 5265054200 Nespresso Next by Delonghi Wood Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 5265533635 CUISIN 4STOST SS NWD | $0.01 | below range | $17.99 | median price of its category |
| Home | 5275804758 DPLY DEMO KEUR BRWR KCFES BLK SHELL | $0.01 | below range | $30.00 | median price of its category |
| Home | 5280863450 DPLY DEMO KEUR BRWR KEXPE RED SHELL | $0.01 | below range | $30.00 | median price of its category |
| Home | 5285700144 DSPWD260WMP SHARK HYDROVAC DISPLAY | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 5314190686 Ninja Thirsti Drink System Display POD Rack DSPWCFPWM6 | $0.01 | below range | $11.91 | median price of the same kind of item |
| Home | 5329710759 Display Smart Robot Vacuum with LIDAR | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 5340416056 Display Nespresso VertuoPlus | $0.01 | below range | $17.99 | median price of its category |
| Home | 5347546854 Ninja® Slushi Professional Frozen Drink Maker Display, DSPFS300WMP | $0.01 | below range | $29.92 | comparable item: Ninja Frozen Treat and Drink Maker |
| Home | 5347596849 Cuisinart Elemental 8 Cup Food Processor Display, FP-8SVWMDIS | $0.01 | below range | $99.95 | comparable item: Cuisinart FP8GMP1 Elemental 8-Cup Food Processor |
| Home | 5373792356 Beautiful PowerExact 2.0 Blender, White Icing by Drew Barrymore NON-WO | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 5378440035 Beautiful 3.5 QT Stand Mixer, White Icing by Drew Barrymore NON-WORKIN | $0.01 | below range | $69.94 | median price of the same kind of item |
| Home | 5525927838 Beast Blender | Ultimate Blending Bundle (Cloud White) DSP | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 5532480271 nutribullet Ultra NB10500 Display | $0.01 | below range | $93.32 | comparable item: Nutribullet NB-50200 Select 2.0 |
| Home | 5534421021 MC Steam Espresso DISPLAY | $0.01 | below range | $22.75 | median price of the same kind of item |
| Home | 5534528391 Ninja Handheld Blender BC200 DSP | $0.01 | below range | $69.00 | comparable item: Ninja Warrior Handheld Blender |
| Home | 5548787422 MC Steam Espresso WOOD DISPLAY | $0.01 | below range | $22.75 | median price of the same kind of item |
| Home | 5555993878 Chefman Espresso Machine with Grinder Wood Display | $0.01 | below range | $48.47 | median price of the same kind of item |
| Home | 5673571363 Beast Mini® Blender Plus (Sand) DSP | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 5685809422 Beast Blender | Ultimate Blending Bundle (Carbon Black) DSP | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 5689657075 Beast Mini® Blender Plus (Mist) DSP | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 5737469293 Chefman Espresso Machine with Grinder Display | $0.01 | below range | $48.47 | median price of the same kind of item |
| Home | 5878999065 EMERGE ALL TERRAIN PET DISPLAY WMT | $0.01 | below range | $30.00 | median price of its category |
| Home | 5954390113 Shark POWERDETECT Upright Vacuum Cleaner Display, DSPAZ4002WMP | $0.01 | below range | $35.23 | median price of the same kind of item |
| Home | 6005476296 Nutribullet 2FT Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 6245902413 ONEPWR EVOLVE PET ELITE BUNDLE DISPLAY WMT | $0.01 | below range | $30.00 | median price of its category |
| Home | 6315410877 Shark Steam Sweep Mop Display, DSPSD200WMP | $0.01 | below range | $99.99 | comparable item: STEAM MOP 4.0 |
| Home | 6331965951 DISPLPAY UNIT FOR - LG NeoChef™ 1.5 cu. ft. Countertop Microwave with  | $0.01 | below range | $89.99 | comparable item: LG LMC0975ST - 0.9 Cu Ft NeoChef Counter Top Micro |
| Home | 6379954286 Shark Primus Cordless Display, DSPIP1250WMP | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 6471711713 Portable Carpet Cleaner Machine Shark StainStriker HairPro Pet Portabl | $0.01 | below range | $19.90 | median price of the same kind of item |
| Home | 6495613007 Shark Floor Cleaning Machine CarpetXpert HairPro Pet with StainStriker | $0.01 | below range | $14.97 | median price of the same kind of item |
| Home | 6532566297 NWD - Non- George Foreman 4-Serving Removable Plate Grill and Panini,  | $0.01 | below range | $45.82 | comparable item: George Foreman 4-Serving Removable Plate Grill and |
| Home | 6536051238 NWD - Non- George Foreman Beyond Grill 7in1 Electric Indoor Grill and  | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 6551306208 NWD - Non- George Foreman 2 Serving Contact Grill | $0.01 | below range | $66.00 | comparable item: George Foreman 5-Serving Black Electric Contact Gr |
| Home | 6612614115 NWD - Non- George Foreman Contact Smokeless - Ready Grill, Family Size | $0.01 | below range | $33.23 | median price of the same kind of item |
| Home | 8170053016 GOUR 4.5Q SLWCK NWD | $0.01 | below range | $17.99 | median price of its category |
| Home | 9793372419 TREND POD BACKER | $0.01 | below range | $12.97 | comparable item: TREND POD DISPLAY MASTER DUBH53615VWM |
| Home | 9835918588 Trend Pod Acrylic Stand | $0.01 | below range | $12.97 | comparable item: TREND POD DISPLAY MASTER DUBH53615VWM |
| Home | 13035519710 Chef iQ Smart Toaster Oven Air Fryer Display NG | $0.01 | below range | $84.06 | comparable item: Chefman 18L Toaster Oven Air Fryer, New |
| Home | 13106605163 SpinWave SmartSteam NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 13324413786 BJ3 Non-Working Standard Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 13338066927 DPLY SLED KEUR BRWR KEXPE V2 RED WMT | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 13368363377 DPLY SLED KEUR BRWR KEXPE V2 TEAL WMT | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 13377701873 PowerClean FurFinder NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 13388862126 DPLY SLED KEUR BRWR KEXPE V2 BLK WMT | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 13393169935 BISSELL Revolution HydroSteam Upright Deep Cleaner NWD 4126 | $0.01 | below range | $89.01 | comparable item: BISSELL Powersteamer Powerbrush Upright Deep Clean |
| Home | 13393219536 BISSELL CrossWave Edge NWD 4158 | $0.01 | below range | $1.00 | comparable item: BISSELL CROSSWAVE HF3 NWD |
| Home | 13396417284 BISSELL CrossWave OmniEdge NWD 4170 | $0.01 | below range | $1.00 | comparable item: BISSELL CROSSWAVE HF3 NWD |
| Home | 13407954849 BISSELL PowerForce PowerBrush NWD 3956 | $0.01 | below range | $91.00 | comparable item: Bissell Bi Powerforce Helix Turbo Rewind Nwd |
| Home | 13411753859 PowerClean NWD | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 13423210023 BISSELL Little Green Mini Portable Deep Cleaner NWD 4101 | $0.01 | below range | $75.00 | comparable item: Bissell Little Green Select Portable Carpet Cleane |
| Home | 13483066236 GAIA BLACK DISPLAY | $0.01 | below range | $30.00 | median price of its category |
| Home | 13622569141 Nespresso Vertuo POP White Coffee and Espresso Maker | $0.01 | below range | $84.97 | comparable item: Nespresso Vertuo Pop Coffee and Espresso Maker by  |
| Home | 13658407425 eufy IndoorCam C220 Display | $0.01 | below range | $30.00 | median price of its category |
| Home | 13743871453 DISPLAY DUUD76211VWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 13842116692 DISPLAY DUUH77410VWM | $0.01 | below range | $12.97 | comparable item: TREND POD DISPLAY MASTER DUBH53615VWM |
| Home | 14173473433 Ninja Creami Swirl Display | $0.01 | below range | $0.98 | comparable item: Ninja Creami Display - XNC300BL |
| Home | 14269255245 PowerXL StirMax Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 14522524949 Ninja Espresso Display | $0.01 | below range | $64.00 | comparable item: Guidecraft Expressions Book Display in Espresso |
| Home | 14526509827 Ninja Single Serve Brewer Display | $0.01 | below range | $44.99 | comparable item: TRU Single Serve Brewer |
| Home | 14692812182 DPLY SLED KEUR BRWR MINIB DUSTY ROSE | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 14717122146 Caffeinator Dual Brew Coffee Maker Display | $0.01 | below range | $37.84 | median price of the same kind of item |
| Home | 14754808945 Caffeinator Dual Brew Coffee Machine | $0.01 | below range | $18.70 | median price of the same kind of item |
| Home | 14760367586 bella 4 QT Slim Air Fryer, Oatmilk, NON-WORKING DISPLAY | $0.01 | below range | $50.51 | comparable item: BELLA 4.6 QT AIR FRYER, BLACK |
| Home | 14771261728 PowerXL AirMax AirFryer 6.3qt Display | $0.01 | below range | $0.98 | comparable item: PowerXL AirMax AirFryer 8qt Display |
| Home | 14787568015 Chef iQ Mini Oven Display | $0.01 | below range | $69.99 | comparable item: GreenLife Mini Oven, Black |
| Home | 14803255002 Chefman 6 Qt. Stainless Steel Air Fryer Display | $0.01 | below range | $68.89 | median price of the same kind of item |
| Home | 14812315402 Crispinator 8 Qt. Air Fryer Display | $0.01 | below range | $84.49 | comparable item: Chefman Crispinator Air Fryer 1700W, 8 Qt, Concret |
| Home | 15095152018 GOURMIA 7Q PAN AIRFRY NWD | $0.01 | below range | $17.99 | median price of its category |
| Home | 15107716433 Smart Touch 4-Slice Digital Toaster Display | $0.01 | below range | $31.99 | comparable item: Chefman Smart Touch 2 Slice Digital Toaster with 6 |
| Home | 15113322969 DUBH59010VWM DISPLAY | $0.01 | below range | $12.97 | comparable item: TREND POD DISPLAY MASTER DUBH53615VWM |
| Home | 15143911170 GO Slim 150 NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 15145118782 GO Pet 303 NWD | $0.01 | below range | $30.00 | median price of its category |
| Home | 15152559919 Smart Touch 2-Slice Digital Toaster Display | $0.01 | below range | $31.99 | comparable item: Chefman Smart Touch 2 Slice Digital Toaster with 6 |
| Home | 15163562399 DPLY SLED KEUR BRWR KEEPL GRAY WMT | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 15451862031 Magic Bullet 4ft Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 15460306250 Nutribullet 4ft Display | $0.01 | below range | $17.99 | median price of its category |
| Home | 15616507536 Ninja Thirsti 3.0 NWD | $0.01 | below range | $29.98 | comparable item: Ninja Thirsti CO2 60ML Bottle |
| Home | 15779019720 Display MC Pro Sage- DSPMC2000WMP | $0.01 | below range | $11.61 | median price of the same kind of item |
| Home | 15827010325 Display French Door Oven- DSPFO100WMP | $0.01 | below range | $17.99 | median price of its category |
| Home | 15921556088 Ninja Traditional Blender Display- INSMTR8WMP1 | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 15923414312 Ninja Traditional Blender Display- INSMTR12WMP1 | $0.01 | below range | $32.84 | median price of the same kind of item |
| Home | 15931565314 Blender Display | $0.01 | below range | $7.79 | comparable item: Blender Display |
| Home | 16201015739 DUUH77310VWM Windtunnel Upright Display Wmt | $0.01 | below range | $30.00 | median price of its category |
| Home | 16308473709 Shark Navigator Robot-DSPRV2100WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 16336920403 Shark DetectPro with DuoClean Detect and Lift-Away- DSPLA800WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 16340767294 Shark Navigator Robot-DSPRV2100AEWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 16341267341 Shark® PowerDetect™ Corded Stick Vacuum Ultra-Light Display - DSPHZ400 | $0.01 | below range | $99.00 | comparable item: Shark Ultra-Light Corded Stick Vacuum |
| Home | 16353618234 Shark® PowerPro™ Flex Reveal Cordless Vacuum NWD - DSPIZ380HWMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 16360602638 Shark Navigator Robot Display - INSRV2100WM | $0.01 | below range | $30.00 | median price of its category |
| Home | 16365114929 Shark® Cordless PowerDetect™ Clean & Empty System NWD - DSPIP3150WMP | $0.01 | below range | $30.00 | median price of its category |
| Home | 16366456734 FreeStyle Max Cordless Stick Vacuum NWD - DSPSV2000WMP | $0.01 | below range | $77.11 | comparable item: Shark Navigator Freestyle Cordless Stick Vacuum, S |
| Home | 16367510085 StainStriker HX100 Display - DSPHX100WMP | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 16369355719 Shark Detect Lift Away ADV Corded Upright Vacuum with PowerFins Detect | $0.01 | below range | $71.34 | comparable item: Shark Navigator Lift-Away ADV Upright Vacuum Clean |
| Home | 16431016438 PowerLifter Allergen Lift-Off NWD | $0.01 | below range | $53.71 | comparable item: BISSELL 29H3W Lift-Off Floors Bagless Vacuum |
| Home | 16431166954 HV Smartwash XL DIsplay DUFH62010VWM | $0.01 | below range | $30.00 | median price of its category |
| Home | 16526068607 SurfaceSense NWD | $0.01 | below range | $1.00 | comparable item: BISSELL CrossWave HydroSteam NWD 3632 |
| Home | 16654209063 BISSELL SpinWave SmartSteam Scrubbing and Sanitizing Mop NWD 4359 | $0.01 | below range | $19.99 | median price of the same kind of item |
| Home | 17219166491 DSPBN300MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17245971035 DSPBC200MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17260100758 DSPBN400MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17275711936 DSPTB400MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17279613854 DSPJC150MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17284665143 DSPBN75MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17297260603 DSPBC100MTRWM | $0.01 | below range | $17.99 | median price of its category |
| Home | 17699066863 Dolphin (2026 Model) E10 Robotic Pool Vacuum Cleaner All Pools up to 3 | $0.01 | below range | $30.00 | median price of its category |
| Home | 17722219032 Dolphin (2026 Model) Explorer E20 Robotic Pool Vacuum Cleaner Pools up | $0.01 | below range | $30.00 | median price of its category |
| Home | 17763654336 Dolphin (2026 Model) Explorer E25 Wi-Fi Robotic Pool Vacuum Cleaner Po | $0.01 | below range | $30.00 | median price of its category |
| Home | 17777364607 Niya (2026 Model) Sonar Ray Robotic Pool Vacuum Cleaner Pools up to 26 | $0.01 | below range | $30.00 | median price of its category |
| Home | 18830070057 DPLY SLED KEUR BRWR KEXPE V2 STONE DISPLAY | $0.01 | below range | $29.67 | median price of the same kind of item |
| Home | 18956611851 Crockpot 7QT Slow Cooker Programmable Gray DISPLAY | $0.01 | below range | $22.37 | comparable item: Crockpot 4.5 qt Slow Cooker SCR450-S |
| Home | 19180408122 Display Analog Flip Oven - DSPSP050WMP | $0.01 | below range | $17.99 | median price of its category |
| Home | 19196053271 Display Crispi Pro Station - DSPAS100WHWM | $0.01 | below range | $0.98 | comparable item: Ninja Crispi Pro Display - XFN100WMPK |
| Home | 19202452862 Display Digital Flip Oven - DSPSP140 | $0.01 | below range | $17.99 | median price of its category |
| Home | 19955119522 Shark Corded Stick Vacuum Display, DSPTV300WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 19962874942 Ninja Mini Luxe Café | $0.01 | below range | $30.00 | median price of its category |
| Home | 19972350733 Shark Cordless Stick Vacuum Display, DSPBU3620WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 19979417315 Shark Cordless Stick Vacuum Display, DSPIA3140WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 19983302589 Shark Corded Stick Vacuum Display, DSPZS500WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 19983765249 Shark Cordless Stick Display, DSPIP1251WMP | $0.01 | below range | $0.98 | comparable item: Shark Upright Vacuum Display, DSPZU50WMP |
| Home | 19985764550 Shark Cordless Stick Vacuum Display, DSPIZ370HWMP | $0.01 | below range | $77.11 | comparable item: Shark Navigator Freestyle Cordless Stick Vacuum, S |
| Home | 19987411603 Shark Upright Vacuum Display, DSPLA802WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 19991805167 Shark Upright Vacuum Display, DSPLX5002WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 19993218850 Shark Cordless Stick Vacuum Display, DSPBU1620WMP | $0.01 | below range | $42.27 | median price of the same kind of item |
| Home | 20002467900 Shark Robot Display, DSPRVB100Z1WM | $0.01 | below range | $30.00 | median price of its category |
| Home | 20031568320 NINJA 4FT BRAND DSP NWD - INSMTR4WMP1 | $0.01 | below range | $0.98 | comparable item: AIR FRYER DSP, DSPAF140WMP |
| Home Improvement | 590318401 Celebrations Fix Single Bucket 1ct W/bucket | $0.01 | below range | $15.15 | median price of its category |
| Household Essentials | 434124640 MB10x14-WM-300CC-50PK | $7,352.94 | above range | $11.96 | median price of its category |
| Household Essentials | 882294390 MB10x14-WM-300CC-200PK | $7,352.94 | above range | $11.96 | median price of its category |
| Household Essentials | 173222814 Dry-Packs 50-1-Gallon Mylar Bags, 10 by 14-Inch for Dried Dehydrafted | $5,617.98 | above range | $39.06 | comparable item: Dry-Packs 100-1-Gallon Mylar Bags, 10" by 14" for  |
| Household Essentials | 600258979 Better Homes&gardens 632pcbhg Eoil Diff | $5,580.80 | above range | $11.96 | median price of its category |
| Household Essentials | 344756098 Scent Sationals 1638pcscts Rs Full | $5,272.00 | above range | $11.96 | median price of its category |
| Household Essentials | 980221012 (12 pack) TIKI® Brand 100 oz. Citronella Scented Torch Fuel with Easy  | $3,778.80 | above range | $230.28 | comparable item: TIKI® Brand 50 oz. BiteFighter Torch Fuel with Eas |
| Household Essentials | 674332923 Great Value Trash Bags Discount Bundle | $3,755.82 | above range | $13.42 | comparable item: Great Value Brand Trash Bags Bundle |
| Household Essentials | 54328493 50, 1 Gallon Mylar Bags & Oxygen Absorbers for Dried Food & Long Term  | $2,507.75 | above range | $16.99 | comparable item: 1 Gallon Mylar Bags & 20 Oxygen Absorbers for Drie |
| Household Essentials | 393515170 Bio-Kleen M05316 Remove All Engine Degreaser and Tar Remover - 55 Gall | $2,330.50 | above range | $11.96 | median price of its category |
| Household Essentials | 648122379 Glade 210pcfaliday Aircar | $2,278.70 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 1330490726 Airwick Aw Sept $10.97 Hp | $2,156.40 | above range | $9.97 | comparable item: Airwick Aw So Lavender & Chamomile 2+5 |
| Household Essentials | 912317912 Glade 200pc Holiday Aircar | $1,994.00 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 939966936 (6 pack) TIKI® Brand 100 oz. Citronella Scented Torch Fuel with Easy P | $1,949.70 | above range | $115.14 | comparable item: TIKI® Brand 50 oz. BiteFighter Torch Fuel with Eas |
| Household Essentials | 19289062 Ridgid K-50-4 Combo Drain Machine | $1,886.24 | above range | $11.96 | median price of its category |
| Household Essentials | 773811417 Reynolds 372pc Rey Big3 Hpal | $1,813.56 | above range | $11.96 | median price of its category |
| Household Essentials | 327575871 (9 pack) Spray Nine, PTX22732, GREZ-OFF Parts Cleaner Degreaser, 1 Eac | $1,728.45 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 16763724162 REYNOLDS WRAP ALUMINUM FOIL FOODWRAP 345 PACK | $1,714.65 | above range | $18.13 | comparable item: (4 pack) (4 Pack) Reynolds Wrap Aluminum Foil, 30  |
| Household Essentials | 153067689 Ergotron SV Life Replacement Battery - medical cart battery - LiFePO4 | $1,623.34 | above range | $12.67 | median price of the same kind of item |
| Household Essentials | 19289061 Ridgid K-50 Sectional Machine | $1,603.14 | above range | $11.96 | median price of its category |
| Household Essentials | 120916197 Handi-foil 380pcspr Kng Bak En | $1,596.64 | above range | $10.57 | median price of the same kind of item |
| Household Essentials | 5268923070 (3 pack) Brillo SnoBol 24 Ounce Toilet Bowl Cleaner | $1,530.00 | above range | $8.34 | comparable item: (2 pack) Brillo SnoBol Extra Strength 24 Ounce Toi |
| Household Essentials | 242110532 Glade 264pcholiday Aircar | $1,526.22 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 992637240 Bona Cleaning/Abrasion Drive Plate, 20", For Use with Sanding Buffers | $1,480.00 | above range | $11.96 | median price of its category |
| Household Essentials | 751594780 Glade 257pcfaliday Aircae | $1,396.36 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 259163350 Glade 1332pcgld Mxd 1332u | $1,340.64 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 42232398 Bird X Combination Sonic/Ultrasound Electronic Repeller | $1,296.62 | above range | $11.96 | median price of its category |
| Household Essentials | 479092079 Selpak 3Ply Individual Roll Toilet Paper - Papel higienico (Pack of 48 | $1,285.11 | above range | $35.29 | comparable item: Selpak 3Ply Individual Roll Toilet Paper - Papel h |
| Household Essentials | 32097973 Champion EasyBird Autofeed 6-Packer Trap with OSC | $1,279.80 | above range | $11.96 | median price of its category |
| Household Essentials | 131208531 (6 pack) Spray Nine, PTX22732, GREZ-OFF Parts Cleaner Degreaser, 1 Eac | $1,176.60 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 499503877 Airwick 102pc Holiday Aircar | $1,152.46 | above range | $8.58 | comparable item: Airwick |
| Household Essentials | 16560666902 70PC Tide 105z NFL HP | $1,116.00 | above range | $15.19 | median per-unit price of comparable items |
| Household Essentials | 709647480 Febreze 201pc Fbz Holiday Hp | $1,108.36 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 44899530 Industrial Cleaner and Degreaser Concentrated, 55 gal Drum | $1,108.31 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 499044771 Ziploc 168pc Zplc Hldy | $1,031.64 | above range | $2.19 | comparable item: ZPLC HLDY STGGAL 19C |
| Household Essentials | 181148217 KLEEN-BORE COPPER CUTTER CLEANING SUPPLIES CLEANER/DEGREASER 2 OZ | $1,023.79 | above range | $1.82 | comparable item: KLEEN-BORE #10 SOLVENTS CLEANER/DEGREASER 2OZ 10 P |
| Household Essentials | 54215894 MOR-ryde 2221003105 Pin Box System RV | $1,003.85 | above range | $11.96 | median price of its category |
| Household Essentials | 162836555 Electric Spin Scrubber, Power Scrubber Rechorgeable Cordless Tub Tile  | $998.89 | above range | $34.23 | comparable item: Musment Electric Spin Scrubber , Cordless Cleaning |
| Household Essentials | 292544496 Electric Spin Scrubber, Power Scrubber Rechorgeable Cordless Tub Tile  | $998.89 | above range | $34.23 | comparable item: Musment Electric Spin Scrubber , Cordless Cleaning |
| Household Essentials | 185071661 Rubbermaid Commercial, RCPT12000GYCT, Overhead Dusting Tool, 12 / Cart | $997.62 | above range | $58.48 | comparable item: Flexible Overhead Dusting Tool with 60 in. Handle |
| Household Essentials | 241221098 Ziploc 184pc Zplc Bts | $996.74 | above range | $8.30 | median price of the same kind of item |
| Household Essentials | 943722398 Sunshine Makers Industrial Cleaner And Degreaser, Concentrated, 55 Gal | $994.86 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 509880685 Airwick 164pc Falliday Airca | $977.72 | above range | $8.58 | comparable item: Airwick |
| Household Essentials | 590759051 Febreze 176pc Fbz Fall Hp | $975.52 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 597558496 Selpak 3Ply Individual Roll Toilet Paper - Papel higienico (Pack of 36 | $965.71 | above range | $35.29 | comparable item: Selpak 3Ply Individual Roll Toilet Paper - Papel h |
| Household Essentials | 273889337 Ziploc 150pczplc Bts Strg | $897.00 | above range | $8.30 | median price of the same kind of item |
| Household Essentials | 18212921571 FIFA - SIDE KICK DISPLAY AIR FRESHENER (FULL OF GOODS) | $894.60 | above range | $7.92 | median price of the same kind of item |
| Household Essentials | 353639084 Duracell Coppertop AA Batteries 10 Count | $888.00 | above range | $6.71 | comparable item: Duracell Coppertop AA Alkaline Batteries, 20 Count |
| Household Essentials | 54801176 Febreze 176pc Fbz Lndry Fav | $869.44 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 685646360 OdoBan Concentrated Odor Eliminator, Eucalyptus, 55 gal Drum | $858.88 | above range | $14.18 | median price of the same kind of item |
| Household Essentials | 983176232 Hefty Trash Bag Discount Bundle | $858.47 | above range | $11.28 | comparable item: Hefty Trash Bag Bundle |
| Household Essentials | 722078855 Hefty Trash Bags Discount Bundle | $857.28 | above range | $9.21 | comparable item: Hefty Brand Trash Bags Bundle |
| Household Essentials | 463166474 Ziploc 130pc Zplc Hldy | $842.40 | above range | $2.19 | comparable item: ZPLC HLDY STGGAL 19C |
| Household Essentials | 35092164 Nam Blaster Ozone Machine | $842.14 | above range | $11.96 | median price of its category |
| Household Essentials | 51671817 HYGEN Quick-Connect Aluminum 48 in. - 96 in. Extension Pole - Yellow ( | $842.04 | above range | $10.17 | comparable item: Rubbermaid Commercial HYGEN HYGEN Quick-Connect Ex |
| Household Essentials | 714230969 Mosquito Magnet Executive Mosquito Trap | $841.73 | above range | $11.88 | median price of the same kind of item |
| Household Essentials | 506943567 Nanoskin CITRO BLAST 1 Pack (All Purpose Clea ner Plus) (Dilution Rati | $836.97 | above range | $11.96 | median price of its category |
| Household Essentials | 219475052 Great Value 180pc Gv Sld Stg Gl | $831.60 | above range | $11.96 | median price of its category |
| Household Essentials | 1915945838 Impact Products Fringe Dust Mop Microfiber Pad - 48" Width X 5" Depth  | $829.29 | above range | $19.99 | median price of the same kind of item |
| Household Essentials | 53433199 Kansas City Royals Headphones - Over the Ear | $806.96 | above range | $15.16 | median price of the same kind of item |
| Household Essentials | 318906327 Febreze 249pc Fbz Holiday Hp | $806.76 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 456706274 Nanoskin HAPPY BUG Bug and Tar Remover 55 Gallons - Car Wash Exterior  | $804.51 | above range | $499.99 | comparable item: Nanoskin HAPPY BUG Bug and Tar Remover 30 Gallons  |
| Household Essentials | 48020331 Renown Hd Industrial Cleaner Degreaser 55Gl/Dr | $779.88 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 638548232 JAM Paper Frosted Lunch Bags, 4.75x8.25x2.5, Pink, 500/Pack, Medium | $773.38 | above range | $4.33 | comparable item: JAM Paper Frosted Lunch Bags, 4.75 x 8.25 x 2.5, P |
| Household Essentials | 46887150 Simple Green Crystal Industrial Cleaner/Degreaser, 55 gal Drum -SMP190 | $757.84 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 734587443 SPRAY DRINK BOTTLE, Case of 96 | $745.08 | above range | $389.40 | comparable item: SPRAY DRINK BOTTLE, Case of 48 |
| Household Essentials | 49152253 Rohl Perrin and Rowe Floor Standing Toilet Brush Holder, Available in  | $728.59 | above range | $17.85 | median price of the same kind of item |
| Household Essentials | 598367447 Ziploc 215pc Zplc Tystry4 | $725.76 | above range | $8.30 | median price of the same kind of item |
| Household Essentials | 745886956 Ziploc 215pczplc Avngrswrs | $725.76 | above range | $8.30 | median price of the same kind of item |
| Household Essentials | 49152262 Rohl Perrin and Rowe Floor Standing Toilet Brush Holder, Available in  | $723.11 | above range | $17.85 | median price of the same kind of item |
| Household Essentials | 49152260 Rohl Perrin and Rowe Floor Standing Toilet Brush Holder, Available in  | $717.60 | above range | $17.85 | median price of the same kind of item |
| Household Essentials | 824203608 Clorox 148pcbv1206-06 Mtbc | $714.08 | above range | $9.18 | median price of the same kind of item |
| Household Essentials | 624682656 Febreze 71pc Fbz Oil 2ct | $705.74 | above range | $6.14 | comparable item: Febreze 60pc Fbz 2ct Auto |
| Household Essentials | 119256320 Woodwick 84pc84 Ct Ww Reed S | $704.76 | above range | $11.96 | median price of its category |
| Household Essentials | 818622073 Duracell PowerSource 660 Batteries | $699.99 | above range | $16.34 | comparable item: Duracell C Alkaline Batteries, 10 Ct |
| Household Essentials | 1205636966 Zone Protects Unscented Insect Repellent Sidekick | $694.08 | above range | $17.95 | comparable item: Zone Protects Unscented Insect Repellent Spray, 10 |
| Household Essentials | 236455459 (30 pack) (30 Pack) Boardwalk Facial Tissue, 100 sheets | $690.57 | above range | $37.50 | comparable item: Bim Bam Boo Facial Tissue, 175 Sheets/Box |
| Household Essentials | 484040055 Glade 204pc Faliday Arcare | $678.62 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 101613466 JAM Paper Frosted Lunch Bags, 3 x 4 x 1.5, Purple, 500/Pack, Small | $670.32 | above range | $7.64 | comparable item: JAM Paper Frosted Lunch Bag, 3 x 4 x 1.5, Purple,  |
| Household Essentials | 571348229 Glade 204pc Holiday Aircar | $665.42 | above range | $7.30 | median price of the same kind of item |
| Household Essentials | 968471986 Bio-Kleen M01316 Glass Kleen All Surface Cleaner - 55 Gallon | $663.49 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 49152247 Rohl Perrin and Rowe Floor Standing Toilet Brush Holder, Available in  | $652.80 | above range | $17.85 | median price of the same kind of item |
| Household Essentials | 1268840132 Duracell Coppertop - For Smoke Alarm, Flashlight, Lantern, Cd Player,  | $652.44 | above range | $356.74 | comparable item: Duracell Coppertop - For Smoke Alarm, Flashlight,  |
| Household Essentials | 316134769 (300 pack) (3 pack) Preparation H Totables Medicated Hemorrhoid Wipes  | $651.44 | above range | $9.97 | median price of the same kind of item |
| Household Essentials | 714428260 Sprayco MY430 MyTube 1.5 Oz. | $646.93 | above range | $0.61 | median per-unit price of comparable items |
| Household Essentials | 814730075 Selpak 3Ply Individual Roll Toilet Paper - Papel higienico (Pack of 24 | $645.34 | above range | $35.29 | comparable item: Selpak 3Ply Individual Roll Toilet Paper - Papel h |
| Household Essentials | 940134963 P F Harris 70pcbed Bug Display | $642.90 | above range | $11.96 | median price of its category |
| Household Essentials | 752274888 Sunshine Makers Crystal Industrial Cleaner/degreaser, 55 Gal Drum | $642.70 | above range | $12.98 | median price of the same kind of item |
| Household Essentials | 672529986 Febreze 198pc Fbz Bts $2.94 | $641.52 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 227057870 Ziploc 160pczplc Bts 160ct | $636.80 | above range | $8.30 | median price of the same kind of item |
| Household Essentials | 286791593 SHOCK LIGHTER, Case of 288 | $632.76 | above range | $21.19 | median price of the same kind of item |
| Household Essentials | 432249010 Airwick 56pc Air Wick 56ct E | $631.38 | above range | $8.58 | comparable item: Airwick |
| Household Essentials | 1546268582 Eveready Max Alkaline 9-volt - For Multipurpose - 9v - 9 V Dc - 96 / C | $630.27 | above range | $340.47 | comparable item: Energizer Max Alkaline 9 Volt - For Multipurpose - |
| Household Essentials | 19684546 SkeeterVac SV5100 Mosquito Killer, Lure, and Eliminator for Backyard I | $629.95 | above range | $11.88 | median price of the same kind of item |
| Household Essentials | 20584661 Rubbermaid Commercial Flow Finishing System, 56" Handle, 18" Mop Head, | $629.49 | above range | $19.99 | median price of the same kind of item |
| Household Essentials | 17062704049 (30 pack) Duracell Coppertop AAA Alkaline Batteries 24/PK | $626.15 | above range | $16.95 | median price of the same kind of item |
| Household Essentials | 17473861679 (16 pack) Kleenex® Universal Multifold Paper Towels, Bulk (02046), 9.2 | $623.36 | above range | $17.65 | median price of the same kind of item |
| Household Essentials | 54310179 Zippo Orange & Black Matte Lighter Prepack | $623.04 | above range | $17.32 | comparable item: Zippo Black and Orange Matte Lighter Prepack |
| Household Essentials | 611244878 Febreze 192pc Fbz Fall Hfec | $622.08 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 543908886 Rubbermaid Commercial 3566GRACT 35G Ranger Rigid Liner - 24.50 gal - 1 | $619.29 | above range | $11.96 | median price of its category |
| Household Essentials | 1810984007 Energizer 357 Watch/calculator - For Multipurpose - Proprietary Size - | $615.62 | above range | $376.80 | comparable item: Energizer 9v - For Multipurpose - - 9v - 9 V Dc -  |
| Household Essentials | 12029886 Koolatron MK14FE Mosquito Trap Cordless 1 Acre with Octenol | $599.99 | above range | $11.88 | median price of the same kind of item |
| Household Essentials | 52639457 Mr. Bar-B-Q SkeeterVac Mosquito Trap, 1 Acre or More | $594.38 | above range | $27.99 | comparable item: Mr. Bar-B-Q SkeeterVac Outdoor Insects Tac Trap, 2 |
| Household Essentials | 55149892 Reynolds Wrap Heavy Duty Aluminum Foil Roll 24" x 1000 ft Silver 627 | $594.34 | above range | $84.99 | comparable item: Heavy Duty Aluminum Foil Roll 12" x 500 ft, Silver |
| Household Essentials | 131532978 Diversey Suma Klear A10 Rinse Aid, 1 gal Bottle, 4/Carton | $592.26 | above range | $101.99 | comparable item: Carpet Extraction Rinse, Floral Scent, 1 gal Bottl |
| Household Essentials | 988934253 Hoover Residential Vacuum All Purpose Cleaning Formula 32Oz | $591.00 | above range | $8.00 | median per-unit price of comparable items |
| Household Essentials | 1177935583 Duracell Coppertop Alkaline Aaa - For Flashlight, Smoke Alarm, Lantern | $589.08 | above range | $385.70 | comparable item: Duracell Coppertop Alkaline Aaa - For Smoke Alarm, |
| Household Essentials | 1066210629 Duracell Coppertop - For Smoke Alarm, Flashlight, Lantern, Calculator, | $574.41 | above range | $385.70 | comparable item: Duracell Coppertop Alkaline Aaa - For Smoke Alarm, |
| Household Essentials | 44890443 Duracell Quantum Alkaline Batteries w/ Duralock Power Preserve Tech 9V | $571.97 | above range | $6.05 | comparable item: Quantum Alkaline Batteries with Duralock Power Pre |
| Household Essentials | 51674544 Rubbermaid Commercial Products H226 60 in. Gripper Aluminum Mop Handle | $571.15 | above range | $35.22 | comparable item: Rubbermaid Commercial FGH225000000 Gripper Aluminu |
| Household Essentials | 856140557 Harvest King Field Pro All Purpose 11.2/-28 | $564.60 | above range | $19.97 | comparable item: Bull Shot All Purpose |
| Household Essentials | 46476921 , Glade Air Freshener And Odor Spray- Super Fresh Scent, 13.8 Oz (Pack | $553.00 | above range | $7.92 | median price of the same kind of item |
| Household Essentials | 52639481 SkeeterVac Mosquito Killer and Eliminator for Backyard Insects | $549.95 | above range | $11.88 | median price of the same kind of item |
| Household Essentials | 696559370 Nanoskin CITRO BLAST 1 Pack (All Purpose Clea ner Plus) (Dilution Rati | $545.00 | above range | $11.96 | median price of its category |
| Household Essentials | 440862188 Duracell, DURMN2400B20CT, CopperTop Alkaline AAA Batteries, 240 / Cart | $544.65 | above range | $16.95 | median price of the same kind of item |
| Household Essentials | 412103002 Febreze 168pc Fbz Ae Ss Oil | $544.00 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 259320876 Febreze 169pc Fbz Btc Lv Hp | $542.00 | above range | $7.85 | median price of the same kind of item |
| Household Essentials | 1748547384 3m™ Easy Shine Applicator Kit W/backpack, 18" Pad, 43" - 63" Handle, G | $520.22 | above range | $11.96 | median price of its category |
| Household Essentials | 120116729 Maxell Alkaline AA General Purpose Battery | $519.99 | above range | $12.71 | comparable item: AA Alkaline General Purpose Battery |
| Household Essentials | 13216314 Tripp Lite - UPS battery - 2 x battery - lead acid - 33 Ah | $519.88 | above range | $108.99 | comparable item: CyberPower RB1280X2D - UPS battery - lead acid - 8 |
| Household Essentials | 289415884 Mayb Generic 80pc May Bst Bty Bx | $518.74 | above range | $59.60 | median per-unit price of comparable items |
| Household Essentials | 142047403 Refresh Your Car 168pcryc Wk5 Asst | $512.28 | above range | $275.28 | comparable item: Refresh Your Car 96pcryc 96ct Sideki |
| Household Essentials | 55348660 Brillo SnoBol 24 Ounce Toilet Bowl Cleaner | $510.00 | above range | $2.78 | comparable item: (2 pack) Brillo SnoBol Extra Strength 24 Ounce Toi |
| Household Essentials | 614379598 50Pcs 55 Gallon Thicken Indoor Outdoor Kitchen Trash Can Garbage Rubbi | $507.79 | above range | $23.38 | comparable item: 50Pcs 55 Gallon Thicken Indoor Outdoor Kitchen Tra |
| Household Essentials | 160879696 Maxell Alkaline AAA Size General Purpose Battery | $503.96 | above range | $12.67 | median price of the same kind of item |
| Household Essentials | 34230688 Grohe 40500000 Allure Brilliant toilet brush set Chrome | $503.49 | above range | $65.45 | comparable item: Grohe Baucosmopolitan 40463001 Toilet Brush Set in |
| Household Essentials | 223551349 Duracell MN2400B16ZCT CopperTop Battery For Smoke Alarm, Flashlight, L | $503.00 | above range | $12.67 | median price of the same kind of item |
| Household Essentials | 1031514408 Duracell Aaa - For Gaming Controllr, Flashlight, Monitoring Device - - | $500.24 | above range | $12.99 | median price of the same kind of item |
| Household Essentials | 638380636 Pine-Sol Sparkling Wave Multi-Surface Cleaner, 57.6 Oz. | $0.50 | far below comparable items | $18.90 | comparable item: (3 pack) (3 pack) Pine-Sol Multi-Surface Cleaner,  |
| Household Essentials | 32636381 BIN DUMP HLF PLT SIZE, 1 EA, (Pack of 1) | $0.03 | below range | $0.93 | median per-unit price of comparable items |
| Household Essentials | 553364584 Refresh Your Car Corrugate Only | $0.03 | below range | $11.96 | median price of its category |
| Household Essentials | 207321507 Dirt Devil Display Dd Spray Mop | $0.01 | below range | $26.46 | comparable item: Dirt Devil Spray Mop |
| Household Essentials | 254761369 Ap and G Inc Catchmaster 812sd Flour and Grain Moth Pantry Pest Traps  | $0.01 | below range | $11.96 | median price of its category |
| Household Essentials | 389400858 Paint 1st Md Pf | $0.01 | below range | $11.96 | median price of its category |
| Household Essentials | 573130848 Little Trees Tray | $0.01 | below range | $19.83 | median price of the same kind of item |
| Household Essentials | 729616804 California Scents 2-sided Fragrance Center (w/r Fc Fd-2s) | $0.01 | below range | $11.97 | median price of the same kind of item |
| Household Essentials | 762498501 NWD PowerPlus Motion Mop Shelf Display | $0.01 | below range | $19.99 | median price of the same kind of item |
| Household Essentials | 771654328 Hoover Display Dd Dry Mop | $0.01 | below range | $19.99 | median price of the same kind of item |
| Household Essentials | 14201314026 City Of Concord City Trash Bag | $0.01 | below range | $3.12 | comparable item: CVP Trash Bag |
| Office Supplies | 156912155 10PK Halloween Pencil Astm 2 | $0.09 | below range | $9.97 | median price of the same kind of item |
| Office Supplies | 36723647 Neon Eraser | $0.05 | below range | $26.06 | comparable item: Ticonderoga Neon Wedge Eraser, 30 Count |
| Office Supplies | 131554105 9-99433 ENVL - 7.25 x 5.5 - WHITE - POCKET - FLAP | $0.05 | below range | $14.24 | median price of its category |
| Office Supplies | 186223964 Services Ticketmaster Ticket | $0.03 | below range | $14.24 | median price of its category |
| Office Supplies | 335155404 Coats & Clark Tray Marker, 4 Feet, 1 Each | $0.03 | below range | $10.14 | median price of the same kind of item |
| Office Supplies | 678678795 Coats & Clark Tray Marker, 8ft, 1 Each | $0.03 | below range | $10.14 | median price of the same kind of item |
| Office Supplies | 15436188 Silly Bandz Fun Shapes - 24 Pack | $0.02 | below range | $14.24 | median price of its category |
| Office Supplies | 322609445 3 IN PDQ BOX | $0.02 | below range | $14.24 | median price of its category |
| Office Supplies | 736893703 24IN PDQ BOX | $0.02 | below range | $14.24 | median price of its category |
| Office Supplies | 3884684 JUMBO PAPER CLIPS | $0.01 | below range | $11.93 | comparable item: Office Impressions Paper Clips, Jumbo, 1000/Pack - |
| Office Supplies | 19340670 Office Impressions Colored Paper, 500 Sh | $0.01 | below range | $5.59 | comparable item: Office Impressions Colored Paper, 500 Sh |
| Office Supplies | 176304993 Scotch Tape Mail Perm Masking Tape Tray | $0.01 | below range | $11.30 | median price of the same kind of item |
| Office Supplies | 189186333 Homedics Demo 6 Sht Micro Cut Shrddr Bd-m600 Disp | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 222427303 Homedics Demo 10 Sht Shredder Bd-10p Disp | $0.01 | below range | $39.76 | comparable item: HoMedics Black & Decker BD-61 Shredder |
| Office Supplies | 262611765 Label Refrigerate APOT 1000 | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 430257767 Homedics Demo 6 Sht Cross Cut Shrddr Bd-s600 Disp | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 580503573 Hairitage Department Manager Envelope | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 595643923 WMT.com Preorder Dummy UPC 19 | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 796069376 Homedics Demo 8 Sht Shredder Cc-800a Disp | $0.01 | below range | $46.26 | median price of the same kind of item |
| Office Supplies | 804138881 Licensed Bts Train - Highlighter | $0.01 | below range | $10.94 | median price of the same kind of item |
| Office Supplies | 841321478 Interactive Commicat Crk Select Card | $0.01 | below range | $25.00 | comparable item: Interactive Commicat Uscell $25 Card |
| Office Supplies | 882625329 Colorbok Wm 28 Slot Paper Rack Display | $0.01 | below range | $23.75 | median price of its category |
| Office Supplies | 934457020 Licensed Bts Train - Marker | $0.01 | below range | $10.14 | median price of the same kind of item |
| Office Supplies | 2744224351 Jabra Walmart 1ft Display | $0.01 | below range | $29.99 | median price of its category |
| Office Supplies | 5853809546 BHG MAGNETIC STRIP RIVER GOLD O/S | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 15616472437 8FT TAPE SIGNAGE 2025 | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 15629123310 4FT TAPE SIGNAGE 2025 | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 15629123311 4FT TAPE BIN STRIP W LTR | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 15645521136 8FT TAPE BIN STRIP W LTR | $0.01 | below range | $14.24 | median price of its category |
| Office Supplies | 16818124328 Winning Ticket Redemption | $0.01 | below range | $14.24 | median price of its category |
| Party & Occasions | 302789365 Way to Celebrate 20 count Cello Easter Mini Treat Bags 4"x6" with 20 W | $0.09 | below range | $2.58 | comparable item: Way to Celebrate 20ct Cello Easter Treat Bags 4"x9 |
| Party & Occasions | 126946337 Way To Celebrate Easter Bunny Ears Headband | $0.05 | below range | $2.04 | comparable item: Way To Celebrate Easter Bunny Ears Headband |
| Party & Occasions | 127401259 Celebrations 32h Xl: Hvd White Heart Pink & Red | $0.05 | below range | $2.37 | comparable item: Celebrations 18h Xl: Hvd White Heart Pink & Red |
| Party & Occasions | 203224987 Way To Celebrate Easter Pom Pom Bunny Ear Headband | $0.05 | below range | $1.61 | comparable item: Way To Celebrate Easter Bunny Ear Headband |
| Party & Occasions | 368147709 Way To Celebrate Easter Bunny Ear Headband | $0.05 | below range | $1.61 | comparable item: Way To Celebrate Easter Bunny Ear Headband |
| Party & Occasions | 950407817 Way To Celebrate Easter Gold Tone Crown Headband | $0.05 | below range | $4.88 | comparable item: Way To Celebrate Silver Crown Headband for Easter |
| Party & Occasions | 16361104855 Mainstays Red Bow Round Plastic Plate, 10.5 in | $0.05 | below range | $0.50 | comparable item: Mainstays - Red Round Plastic Plate, 10.5-inch |
| Party & Occasions | 138915089 Seasonal Happy Birthday Printed Streamer | $0.03 | below range | $5.44 | comparable item: Happy Birthday Jointed Banner, 1pk |
| Party & Occasions | 982372034 CARDBOARD 8 PEG SIDEKICK | $0.02 | below range | $11.48 | median price of its category |
| Party & Occasions | 685698692 Greeting Cards* | $0.01 | below range | $4.80 | comparable item: Hallmark Greeting Cards 5.5"x4" (25 Count) |
| Party & Occasions | 808660381 Harman Party Box Demo Station | $0.01 | below range | $11.48 | median price of its category |
| Party & Occasions | 944017180 Eero Pdq With Pull Cards | $0.01 | below range | $11.48 | median price of its category |
| Party & Occasions | 5395277452 Trend Pod WOW Header - DAP 5005 | $0.01 | below range | $18.10 | median price of its category |
| Party & Occasions | 5875461851 Wk 27 Trend Pod WOW Header - DAP 5064 | $0.01 | below range | $18.10 | median price of its category |
| Personal Care | 509970023 Equate 1119pc Suncare S2 | $9,961.41 | above range | $12.45 | median price of its category |
| Personal Care | 2699924679 Oral B 371pc Orl-shv Holplt | $8,842.66 | above range | $11.38 | median price of its category |
| Personal Care | 571508302 Equate 964pc Suncare S1 | $7,458.51 | above range | $12.45 | median price of its category |
| Personal Care | 5083752440 Gillette Intimate Electric Pubic Hair Trimmer for Men, Waterproof Body | $6,719.35 | above range | $44.94 | comparable item: Gillette Intimate i3 Men's Pubic Hair Electric Tri |
| Personal Care | 698840638 10" King Organic cotton and wool futon mattress | $3,544.50 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 737041537 8" King Organic cotton and wool futon mattress | $3,053.01 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 797413258 100 Cases of 12 Pink Pearlized Liquid Lotion Hand Wash Soap 800-ml Dis | $2,845.38 | above range | $57.99 | comparable item: LifeSupplyUSA Case of 24 Pink Pearlized Liquid Lot |
| Personal Care | 18871403857 588 pc ICE BREAKER I-CUBE AST H MOD | $2,751.84 | above range | $435.88 | median per-unit price of comparable items |
| Personal Care | 913487169 10" Full Organic cotton and wool futon mattress | $2,385.92 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 717610670 10" Queen Organic cotton and wool futon mattress | $2,371.59 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 17761873750 (45 pack) Quip Adult Electric Rechargeable Toothbrush Full Head, Midni | $2,369.70 | above range | $52.66 | comparable item: Quip Adult Electric Rechargeable Toothbrush Full H |
| Personal Care | 796455643 8" Queen Organic cotton and wool futon mattress | $2,212.25 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 17773274987 (100 pack) Ear and Nose Hair Trimmer for Men, Upgraded Version Profess | $2,101.00 | above range | $21.01 | comparable item: Ear and Nose Hair Trimmer for Men, Upgraded Versio |
| Personal Care | 768783691 3" King Organic cotton and wool futon mattress | $2,017.55 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 874876709 8" Twin Organic cotton and wool futon mattress | $1,789.67 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 37066098 DreamLine 34 in. D x 60 in. W x 75 5/8 in. H Right Drain Acrylic Showe | $1,589.99 | above range | $836.00 | comparable item: DreamLine 34 in. D x 60 in. W x 76 3/4 in. H Right |
| Personal Care | 37066063 DreamLine 34 in. D x 60 in. W x 75 5/8 in. H Center Drain Acrylic Show | $1,551.77 | above range | $936.00 | comparable item: DreamLine 34 in. D x 60 in. W x 76 3/4 in. H Cente |
| Personal Care | 249083577 3" Twin XL Organic cotton and wool futon mattress | $1,498.98 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 663182840 Equate 144pc Eq Sun Twin Hp | $1,437.12 | above range | $715.54 | comparable item: EQ 20PC SK BTB BARBI |
| Personal Care | 163322686 5" Full Organic cotton and wool futon mattress | $1,422.49 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 845651311 5" Twin XL Organic cotton and wool futon mattress | $1,396.60 | above range | $39.77 | median price of the same kind of item |
| Personal Care | 13474424820 Dove Superbowl End Cap | $1,240.00 | above range | $11.38 | median price of its category |
| Personal Care | 17033618829 80 pc PlusOne Menopause Awareness Month Feature | $1,195.00 | above range | $16.00 | median price of its category |
| Personal Care | 37066080 DreamLine 34 in. D x 60 in. W x 75 5/8 in. H Left Drain Acrylic Shower | $1,159.99 | above range | $985.99 | comparable item: DreamLine 34 in. D x 60 in. W x 76 3/4 in. H Left  |
| Personal Care | 5553397147 (8 pack) EVO IRM-1 Rechargeable Iron Man Sonic Toothbrush with Travel  | $1,159.92 | above range | $9.98 | median price of the same kind of item |
| Personal Care | 23520843 Portable Cordless Water Flosser – Rechargeable Oral Irrigator with 3 P | $1,143.90 | above range | $26.39 | comparable item: Water Flosser Cordless,Portable Rechargeable Oral  |
| Personal Care | 564878001 Intuition Women's Razor System 152Pc Ec F'18 | $1,136.92 | above range | $13.52 | median price of the same kind of item |
| Personal Care | 144189622 Haws AXION MSR Combination Eye/Face Wash And Shower | $1,105.88 | above range | $11.46 | median price of the same kind of item |
| Personal Care | 283406569 Secret 141pc Os Sec Sprayec | $1,003.77 | above range | $38.38 | median per-unit price of comparable items |
| Personal Care | 824611914 Bic Mixed Shave Display | $1,003.30 | above range | $262.08 | comparable item: BIC Mixed Shave Disp |
| Personal Care | 175432420 Loofah Soap Exfoliating Scrub Soap Bar Beach Breeze | $0.10 | far below comparable items | $3.37 | median per-unit price of comparable items |
| Personal Care | 22614745 Free His/her Gillette Razors Courtesy Of | $0.02 | below range | $23.54 | comparable item: His n Hers Razors Assortment Pack |
| Personal Care | 21472859 Suave Water Pebble | $0.01 | below range | $31.95 | median price of the same kind of item |
| Personal Care | 862981383 Magic Bullet Veggie Bullet Compact Display | $0.01 | below range | $16.00 | median price of its category |
| Pets | 155730056 Clear For Life 500T Rectangle Acrylic Aquarium - Sapphire Blue Back | $6,816.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 165889819 Clear For Life 500T Rectangle Acrylic Aquarium - Black Back | $6,816.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 931921923 Clear For Life 500T Rectangle Acrylic Aquarium - Blue Back | $6,816.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 185405164 Clear For Life 500T Rectangle Acrylic Aquarium - Clear Back | $6,402.00 | above range | $1,164.00 | comparable item: Clear For Life 180R Rectangle Acrylic Aquarium - C |
| Pets | 138280983 Clear For Life 360T Rectangle Acrylic Aquarium - Black Back | $5,394.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 182974550 Clear For Life 360T Rectangle Acrylic Aquarium - Blue Back | $5,358.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 195798721 Clear For Life 360T Rectangle Acrylic Aquarium - Sapphire Blue Back | $5,358.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 163473746 Clear For Life 360T Rectangle Acrylic Aquarium - Clear Back | $4,930.00 | above range | $1,164.00 | comparable item: Clear For Life 180R Rectangle Acrylic Aquarium - C |
| Pets | 902559603 135 Gallon Glass Fish Tank Aquarium with LED Light and Stand Bundle | $4,482.75 | above range | $149.00 | median price of the same kind of item |
| Pets | 403173815 ALLGREEN Pet 15 x 95 FT Artificial Grass for Pet Dog Potty Training In | $4,397.25 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 922318087 MegaGrass MegaPet Pro 15 x 100 ft Artificial Grass for Pet Dog Potty I | $3,930.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 428541025 MegaGrass MegaPet Pro 15 x 99 ft Artificial Grass for Pet Dog Potty In | $3,885.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 54192108 Heel O Matic Heelomatic Trainer | $3,876.83 | above range | $19.68 | median price of its category |
| Pets | 802963376 MegaGrass MegaPet Pro 15 x 98 ft Artificial Grass for Pet Dog Potty In | $3,852.06 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 703228956 Cute kittyAutomation generated BV title | $3,836.67 | above range | $19.68 | median price of its category |
| Pets | 711114891 MegaGrass MegaPet Pro 15 x 96 ft Artificial Grass for Pet Dog Potty In | $3,786.26 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 474231293 MegaGrass MegaPet Pro 15 x 95 ft Artificial Grass for Pet Dog Potty In | $3,684.06 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 717372786 MegaGrass MegaPet Pro 15 x 94 ft Artificial Grass for Pet Dog Potty In | $3,650.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 448822623 MegaGrass MegaPet Pro 15 x 93 ft Artificial Grass for Pet Dog Potty In | $3,616.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 228304876 MegaGrass MegaPet Pro 15 x 92 ft Artificial Grass for Pet Dog Potty In | $3,584.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 476833062 MegaGrass MegaPet Pro 15 x 91 ft Artificial Grass for Pet Dog Potty In | $3,551.06 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 100833784 MegaGrass MegaPet Pro 15 x 90 ft Artificial Grass for Pet Dog Potty In | $3,518.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 875952827 MegaGrass MegaPet Pro 15 x 87 ft Artificial Grass for Pet Dog Potty In | $3,419.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 136925329 Clear For Life 270S Rectangle Acrylic Aquarium - Black Back | $3,406.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 746053200 Clear For Life 270S Rectangle Acrylic Aquarium - Blue Back | $3,406.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 600888021 MegaGrass MegaPet Pro 15 x 86 ft Artificial Grass for Pet Dog Potty In | $3,385.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 170119891 Clear For Life 270S Rectangle Acrylic Aquarium - Sapphire Blue Back | $3,384.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 996694168 MegaGrass MegaPet Pro 15 x 84 ft Artificial Grass for Pet Dog Potty In | $3,320.06 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 121318023 MegaGrass MegaPet Platinum 15 x 75 ft Artificial Grass for Pet Dog Pot | $3,301.20 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 193240255 MegaGrass MegaPet Pro 15 x 83 ft Artificial Grass for Pet Dog Potty In | $3,287.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 983973870 ALLGREEN Pet 15 x 97 FT Artificial Grass for Pet Dog Potty Training In | $3,242.57 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 933887556 MegaGrass MegaPet Pro 15 x 81 ft Artificial Grass for Pet Dog Potty In | $3,220.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 639474940 ALLGREEN Pet 15 x 96 FT Artificial Grass for Pet Dog Potty Training In | $3,209.14 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 439879922 MegaGrass MegaPet Pro 15 x 80 ft Artificial Grass for Pet Dog Potty In | $3,188.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 969533554 MegaGrass MegaPet Pro 15 x 79 ft Artificial Grass for Pet Dog Potty In | $3,154.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 439250102 ALLGREEN Pet 15 x 94 FT Artificial Grass for Pet Dog Potty Training In | $3,142.29 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 264286414 MegaGrass MegaPet Platinum 15 x 100 ft Artificial Grass for Pet Dog Po | $3,067.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 158952688 Clear For Life 300T Rectangle UniQuarium - Sapphire Blue Back | $3,060.00 | above range | $755.00 | comparable item: Clear For Life 65R Rectangle UniQuarium - Sapphire |
| Pets | 471962083 Clear For Life 300T Rectangle UniQuarium - Black Back | $3,060.00 | above range | $19.68 | median price of its category |
| Pets | 507937393 Clear For Life 300T Rectangle UniQuarium - Blue Back | $3,060.00 | above range | $19.68 | median price of its category |
| Pets | 354456563 ALLGREEN Pet 15 x 91 FT Artificial Grass for Pet Dog Potty Training In | $3,042.00 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 704651856 ALLGREEN Pet 15 x 70 FT Artificial Grass for Pet Dog Potty Training In | $3,042.00 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 405288182 MegaGrass MegaPet Platinum 15 x 99 ft Artificial Grass for Pet Dog Pot | $3,034.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 498774847 MegaGrass MegaPet Platinum 15 x 98 ft Artificial Grass for Pet Dog Pot | $3,008.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 159573450 Clear For Life 270S Rectangle Acrylic Aquarium - Clear Back | $2,988.00 | above range | $1,164.00 | comparable item: Clear For Life 180R Rectangle Acrylic Aquarium - C |
| Pets | 793857281 MegaGrass MegaPet Platinum 15 x 97 ft Artificial Grass for Pet Dog Pot | $2,982.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 981973628 ALLGREEN Pet 15 x 89 FT Artificial Grass for Pet Dog Potty Training In | $2,975.14 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 697484616 MegaGrass MegaPet Platinum 15 x 96 ft Artificial Grass for Pet Dog Pot | $2,956.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 848462326 ALLGREEN Pet 15 x 88 FT Artificial Grass for Pet Dog Potty Training In | $2,941.71 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 724393189 MegaGrass MegaPet Platinum 15 x 95 ft Artificial Grass for Pet Dog Pot | $2,930.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 249660305 ALLGREEN Pet 15 x 87 FT Artificial Grass for Pet Dog Potty Training In | $2,908.29 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 407475027 MegaGrass MegaPet Platinum 15 x 94 ft Artificial Grass for Pet Dog Pot | $2,904.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 407080978 MegaGrass MegaPet Platinum 15 x 93 ft Artificial Grass for Pet Dog Pot | $2,878.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 722843993 MegaGrass MegaPet Pro 15 x 72 ft Artificial Grass for Pet Dog Potty In | $2,853.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 848375615 MegaGrass MegaPet Platinum 15 x 92 ft Artificial Grass for Pet Dog Pot | $2,852.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 942835443 ALLGREEN Pet 15 x 85 FT Artificial Grass for Pet Dog Potty Training In | $2,841.43 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 229122722 MegaGrass MegaPet Platinum 15 x 91 ft Artificial Grass for Pet Dog Pot | $2,826.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 218742084 MegaGrass MegaPet Pro 15 x 71 ft Artificial Grass for Pet Dog Potty In | $2,821.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 513619872 ALLGREEN Pet 15 x 84 FT Artificial Grass for Pet Dog Potty Training In | $2,808.00 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 179382952 MegaGrass MegaPet Platinum 15 x 90 ft Artificial Grass for Pet Dog Pot | $2,799.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 356314278 MegaGrass MegaPet Pro 15 x 97 ft Artificial Grass for Pet Dog Potty In | $2,788.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 174122618 MegaGrass MegaPet Platinum 15 x 89 ft Artificial Grass for Pet Dog Pot | $2,773.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 515050037 MegaGrass MegaPet Pro 15 x 69 ft Artificial Grass for Pet Dog Potty In | $2,755.86 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 797650666 MegaGrass MegaPet Platinum 15 x 88 ft Artificial Grass for Pet Dog Pot | $2,747.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 444922423 ALLGREEN Pet 15 x 82 FT Artificial Grass for Pet Dog Potty Training In | $2,741.14 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 676310623 MegaGrass MegaPet Platinum 15 x 87 ft Artificial Grass for Pet Dog Pot | $2,721.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 765831998 ALLGREEN Pet 15 x 81 FT Artificial Grass for Pet Dog Potty Training In | $2,707.71 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 304702571 MegaGrass MegaPet Platinum 15 x 86 ft Artificial Grass for Pet Dog Pot | $2,695.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 491951927 MegaGrass MegaPet Pro 15 x 67 ft Artificial Grass for Pet Dog Potty In | $2,688.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 659651203 ALLGREEN Pet 15 x 80 FT Artificial Grass for Pet Dog Potty Training In | $2,674.29 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 260198524 MegaGrass MegaPet Platinum 15 x 85 ft Artificial Grass for Pet Dog Pot | $2,669.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 333276793 MegaGrass MegaPet Pro 15 x 66 ft Artificial Grass for Pet Dog Potty In | $2,656.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 808852706 ALLGREEN Pet 15 x 79 FT Artificial Grass for Pet Dog Potty Training In | $2,640.86 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 409074057 ALLGREEN Pet 15 x 78 FT Artificial Grass for Pet Dog Potty Training In | $2,607.43 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 645088281 MegaGrass MegaPet Platinum 15 x 84 ft Artificial Grass for Pet Dog Pot | $2,593.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 856784125 MegaGrass MegaPet Pro 15 x 64 ft Artificial Grass for Pet Dog Potty In | $2,590.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 755342933 MegaGrass MegaPet Platinum 15 x 83 ft Artificial Grass for Pet Dog Pot | $2,567.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 739268703 MegaGrass MegaPet Pro 15 x 89 ft Artificial Grass for Pet Dog Potty In | $2,549.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 803358004 MegaGrass MegaPet Platinum 15 x 82 ft Artificial Grass for Pet Dog Pot | $2,541.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 144864096 Clear For Life 300T Rectangle Acrylic Aquarium - Black Back | $2,526.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 146629448 Clear For Life 300T Rectangle Acrylic Aquarium - Sapphire Blue Back | $2,526.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 721476117 Clear For Life 240S Rectangle Acrylic Aquarium - Black Back | $2,526.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 731111534 Clear For Life 240S Rectangle Acrylic Aquarium - Sapphire Blue Back | $2,526.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 930506443 Clear For Life 240S Rectangle Acrylic Aquarium - Blue Back | $2,526.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 995759081 Clear For Life 300T Rectangle Acrylic Aquarium - Blue Back | $2,526.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 963280815 MegaGrass MegaPet Pro 15 x 62 ft Artificial Grass for Pet Dog Potty In | $2,523.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 361435358 MegaGrass MegaPet Platinum 15 x 81 ft Artificial Grass for Pet Dog Pot | $2,515.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 768444649 ALLGREEN Pet 15 x 75 FT Artificial Grass for Pet Dog Potty Training In | $2,507.14 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 792616110 Clear For Life 240R Rectangle UniQuarium - Blue Back | $2,491.00 | above range | $19.68 | median price of its category |
| Pets | 805979229 MegaGrass MegaPet Platinum 15 x 80 ft Artificial Grass for Pet Dog Pot | $2,488.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 103754630 Clear For Life 240R Rectangle UniQuarium - Black Back | $2,478.00 | above range | $879.00 | comparable item: Clear For Life 75R Rectangle UniQuarium - Black Ba |
| Pets | 647406199 MegaGrass MegaPet Platinum 15 x 79 ft Artificial Grass for Pet Dog Pot | $2,462.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 220269747 MegaGrass MegaPet Pro 15 x 60 ft Artificial Grass for Pet Dog Potty In | $2,457.66 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 894187851 MegaGrass MegaPet Pro 15 x 85 ft Artificial Grass for Pet Dog Potty In | $2,455.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 614972540 ALLGREEN Pet 15 x 73 FT Artificial Grass for Pet Dog Potty Training In | $2,440.29 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 861969235 MegaGrass MegaPet Platinum 15 x 78 ft Artificial Grass for Pet Dog Pot | $2,436.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 189792642 Clear For Life 225S Rectangle Acrylic Aquarium - Black Back | $2,421.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 460899858 MegaGrass MegaPet Platinum 15 x 77 ft Artificial Grass for Pet Dog Pot | $2,410.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 157395096 Clear For Life 225S Rectangle Acrylic Aquarium - Sapphire Blue Back | $2,406.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 663556359 Clear For Life 225S Rectangle Acrylic Aquarium - Blue Back | $2,406.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 47244457 (16 pack) (16 pack) (16 Pack) Pedigree Little Champions Senior Complet | $2,389.92 | above range | $19.04 | comparable item: Pedigree Little Champions Senior Complete With Lam |
| Pets | 170268007 MegaGrass MegaPet Platinum 15 x 76 ft Artificial Grass for Pet Dog Pot | $2,384.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 295121111 MegaGrass MegaPet Pro 15 x 82 ft Artificial Grass for Pet Dog Potty In | $2,384.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 491109225 ALLGREEN Pet 15 x 71 FT Artificial Grass for Pet Dog Potty Training In | $2,373.43 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 702432320 MegaGrass MegaPet Platinum 15 x 74 ft Artificial Grass for Pet Dog Pot | $2,332.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 297939828 ALLGREEN Pet 15 x 69 FT Artificial Grass for Pet Dog Potty Training In | $2,306.57 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 216512939 MegaGrass MegaPet Platinum 15 x 73 ft Artificial Grass for Pet Dog Pot | $2,306.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 197958537 MegaGrass MegaPet Pro 15 x 78 ft Artificial Grass for Pet Dog Potty In | $2,290.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 111994118 MegaGrass MegaPet Platinum 15 x 72 ft Artificial Grass for Pet Dog Pot | $2,280.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 594737903 Clear For Life 200R Rectangle UniQuarium - Sapphire Blue Back | $2,262.00 | above range | $1,920.00 | comparable item: Clear For Life 180R Rectangle UniQuarium - Sapphir |
| Pets | 803251194 MegaGrass MegaPet Pro 15 x 56 ft Artificial Grass for Pet Dog Potty In | $2,256.06 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 578677106 MegaGrass MegaPet Platinum 15 x 71 ft Artificial Grass for Pet Dog Pot | $2,254.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 466846039 Clear For Life 200R Rectangle UniQuarium - Blue Back | $2,250.00 | above range | $1,920.00 | comparable item: Clear For Life 180R Rectangle UniQuarium - Blue Ba |
| Pets | 670556461 Clear For Life 200R Rectangle UniQuarium - Black Back | $2,250.00 | above range | $19.68 | median price of its category |
| Pets | 399713603 ALLGREEN Pet 15 x 67 FT Artificial Grass for Pet Dog Potty Training In | $2,239.71 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 618243479 MegaGrass MegaPet Platinum 15 x 70 ft Artificial Grass for Pet Dog Pot | $2,227.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 545119415 MegaGrass MegaPet Pro 15 x 55 ft Artificial Grass for Pet Dog Potty In | $2,222.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 235739970 MegaGrass MegaPet Pro 15 x 77 ft Artificial Grass for Pet Dog Potty In | $2,216.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 464774611 ALLGREEN Pet 10 x 99 FT Artificial Grass for Pet Dog Potty Training In | $2,206.29 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 408580409 MegaGrass MegaPet Platinum 15 x 69 ft Artificial Grass for Pet Dog Pot | $2,201.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 243963390 MegaGrass MegaPet Pro 15 x 54 ft Artificial Grass for Pet Dog Potty In | $2,190.26 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 129432931 Clear For Life 180S Rectangle Acrylic Aquarium - Black Back | $2,187.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Bl |
| Pets | 151239666 Clear For Life 180S Rectangle Acrylic Aquarium - Sapphire Blue Back | $2,187.00 | above range | $582.00 | comparable item: Clear For Life 90R Rectangle Acrylic Aquarium - Sa |
| Pets | 104284986 Clear For Life 300T Rectangle Acrylic Aquarium - Clear Back | $2,185.00 | above range | $1,164.00 | comparable item: Clear For Life 180R Rectangle Acrylic Aquarium - C |
| Pets | 205686937 ALLGREEN Pet 10 x 98 FT Artificial Grass for Pet Dog Potty Training In | $2,184.00 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 812571852 MegaGrass MegaPet Platinum 15 x 68 ft Artificial Grass for Pet Dog Pot | $2,175.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 954051405 Clear For Life 180S Rectangle Acrylic Aquarium - Blue Back | $2,172.00 | above range | $340.00 | comparable item: Clear For Life 15R Rectangle Acrylic Aquarium - Bl |
| Pets | 316843926 ALLGREEN Pet 10 x 97 FT Artificial Grass for Pet Dog Potty Training In | $2,161.71 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 423330474 Clear For Life 225S Rectangle Acrylic Aquarium - Clear Back | $2,153.00 | above range | $1,164.00 | comparable item: Clear For Life 180R Rectangle Acrylic Aquarium - C |
| Pets | 413095486 MegaGrass MegaPet Platinum 15 x 67 ft Artificial Grass for Pet Dog Pot | $2,149.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 628872331 MegaGrass MegaPet Pro 15 x 74 ft Artificial Grass for Pet Dog Potty In | $2,145.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 987966450 ALLGREEN Pet 10 x 96 FT Artificial Grass for Pet Dog Potty Training In | $2,139.43 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 474135585 MegaGrass MegaPet Pro 15 x 52 ft Artificial Grass for Pet Dog Potty In | $2,124.46 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 557701802 MegaGrass MegaPet Platinum 15 x 66 ft Artificial Grass for Pet Dog Pot | $2,123.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 818794205 MegaGrass MegaPet Pro 15 x 73 ft Artificial Grass for Pet Dog Potty In | $2,122.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 507123900 ALLGREEN Pet 10 x 95 FT Artificial Grass for Pet Dog Potty Training In | $2,117.14 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 775952120 ALLGREEN Pet 15 x 63 FT Artificial Grass for Pet Dog Potty Training In | $2,106.00 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 24503041 ShelterLogic 24 x 22 x 13 ft Green Run-In Shelter | $2,098.99 | above range | $19.68 | median price of its category |
| Pets | 154035957 Clear For Life 240S Rectangle Acrylic Aquarium - Clear Back | $2,092.00 | above range | $1,164.00 | comparable item: Clear For Life 180R Rectangle Acrylic Aquarium - C |
| Pets | 310483513 ALLGREEN Pet 15 x 62 FT Artificial Grass for Pet Dog Potty Training In | $2,072.57 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 455719568 ALLGREEN Pet 10 x 93 FT Artificial Grass for Pet Dog Potty Training In | $2,072.57 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 247525821 MegaGrass MegaPet Pro 15 x 70 ft Artificial Grass for Pet Dog Potty In | $2,051.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 923175936 MegaGrass MegaPet Platinum 15 x 65 ft Artificial Grass for Pet Dog Pot | $2,047.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 990710076 ALLGREEN Pet 15 x 61 FT Artificial Grass for Pet Dog Potty Training In | $2,039.14 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 479797292 ALLGREEN Pet 10 x 91 FT Artificial Grass for Pet Dog Potty Training In | $2,028.00 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 769148528 MegaGrass MegaPet Platinum 15 x 64 ft Artificial Grass for Pet Dog Pot | $2,021.00 | above range | $770.00 | comparable item: MegaGrass MegaPet Platinum 15 x 18 ft Artificial G |
| Pets | 839455099 ALLGREEN Pet 15 x 43 FT Artificial Grass for Pet Dog Potty Training In | $2,012.40 | above range | $802.29 | comparable item: ALLGREEN Pet 10 x 36 FT Artificial Grass for Pet D |
| Pets | 627336877 MegaGrass MegaPet Pro 15 x 68 ft Artificial Grass for Pet Dog Potty In | $2,004.00 | above range | $1,247.00 | comparable item: MegaGrass MegaPet Pro 15 x 38 ft Artificial Grass  |
| Pets | 162772768 50” Stainless Steel Large Dog Grooming Bath Tub Kit, Pet Bathing Stati | $1,999.99 | above range | $862.99 | comparable item: CO-Z 50 Stainless Steel Dog Grooming Bath Tub Kit, |
| Pets | 978675949 Cone Protective Collar for Pet Dogs Cats Wound Healing Protection Cove | $1.12 | far below comparable items | $22.70 | median price of the same kind of item |
| Pets | 20622622446 (3 pack) (3 pack) (3 pack) Feline Fresh Natural Pine Cat Litter, 7-lb | $1.02 | far below comparable items | $4.07 | comparable item: (4 pack) Feline Fresh Natural Pine Cat Litter, 7-l |
| Pets | 10318939 (24 Pack) Pedigree Little Champions Chicken Flavor Wet Dog Food, 5.3 O | $0.98 | far below comparable items | $28.56 | comparable item: Pedigree Little Champions Meaty Ground Dinner With |
| Pets | 130545773 Purina Pro Plan Urinary Tract Health Wet Cat Food Ocean Whitefish, 3 o | $0.89 | far below comparable items | $47.04 | comparable item: Purina Pro Plan Urinary Tract Health, Ocean Whitef |
| Pets | 21668251 Purina Fancy Feast Grilled Kitten Food, Wet Cat Food, Turkey & Giblets | $0.76 | far below comparable items | $21.12 | comparable item: Purina Fancy Feast Grilled Kitten Food, Wet Cat Fo |
| Pets | 1880266829 (2 pack) Feline Fresh Natural Pine Cat Litter, 7-lb | $0.68 | far below comparable items | $2.71 | comparable item: (4 pack) Feline Fresh Natural Pine Cat Litter, 7-l |
| Pets | 24107892 Feline Fresh Natural Pine Cat Litter, 7-lb | $0.34 | far below comparable items | $7.12 | median per-unit price of comparable items |
| Pets | 40618709 9Lives Meaty Paté With Real Beef Wet Cat Food, 13-Ounce | $0.17 | far below comparable items | $27.84 | comparable item: (2 pack) 9Lives Meaty Paté with Real Beef Wet Cat  |
| Pets | 47220708 Free Litter! Littermaid 980 Multi-Cat Self-Cleaning Litter Box with Fr | $0.06 | below range | $109.97 | comparable item: Free Litter! Littermaid 980 Multi-Cat Self-Cleanin |
| Pets | 158097545 Fantasy Aquarium (Nintendo DS) | $0.03 | below range | $15.00 | comparable item: Paws & Claws Dogs & cats (Nintendo DS) |
| Pets | 16401748 Iams Puppy Pack - free with purchase of any Iams Puppy food item | $0.01 | below range | $13.48 | comparable item: Iams Orginal Dry Puppy Food 8lb |
| Pets | 480559506 Voyager Step-In Air Dog Harness - All Weather Mesh, Step in Vest Harne | $0.01 | below range | $14.99 | comparable item: Voyager Step-In Air Dog Harness - All Weather Mesh |
| Pets | 758450316 Serta Gel Ortho Quilted Couch-D-MOF | $0.01 | below range | $19.68 | median price of its category |
| Pets | 974087509 .com Toy Dog (duplicate Upc #) | $0.01 | below range | $11.98 | median price of the same kind of item |
| Pets | 1978409147 PowerLifter Pet Rewind NWD 3405 | $0.01 | below range | $19.68 | median price of its category |
| Pets | 19250571762 PET HONESTY DOG ASSORTMENT PDQ 9X40X11 - PERMANENT On Shelf PDQ Tray - | $0.01 | below range | $24.08 | median price of the same kind of item |
| Pets | 19269412271 PET HONESTY CAT ASSORTMENT PDQ 7X25X11 - PERMANENT On Shelf PDQ Tray - | $0.01 | below range | $24.08 | median price of the same kind of item |
| Premium Beauty | 180570809 Rotiform R139 Kps 18X8.5 5X100 35Et 66.56Cb Matte Black Wheel | $4,288.61 | above range | $30.07 | median price of its category |
| Premium Beauty | 17779951575 (24 pack) Calvin Klein CK BE Eau De Toilette Spray (Unisex) for Women  | $2,352.00 | above range | $34.96 | median price of the same kind of item |
| Premium Beauty | 954094694 WS 36 Magnifying Makeup Mirror in Shiny Gold | $2,114.00 | above range | $527.78 | comparable item: WS 33 Magnifying Makeup Mirror in Polished Chrome |
| Premium Beauty | 226932738 WS 36 Magnifying Makeup Mirror in Matte Gold | $1,869.84 | above range | $672.00 | comparable item: WS 33 Magnifying Makeup Mirror in Matte Black |
| Premium Beauty | 269841790 WS 36 Magnifying Makeup Mirror in Dark Bronze | $1,869.84 | above range | $527.78 | comparable item: WS 33 Magnifying Makeup Mirror in Polished Chrome |
| Premium Beauty | 597166888 WS 36 Magnifying Makeup Mirror in Matte Nickel | $1,750.00 | above range | $672.00 | comparable item: WS 33 Magnifying Makeup Mirror in Matte Black |
| Premium Beauty | 716821004 WS 36 Magnifying Makeup Mirror in Polished Chrome | $1,750.00 | above range | $527.78 | comparable item: WS 33 Magnifying Makeup Mirror in Polished Chrome |
| Premium Beauty | 437873797 Sebastian Drench Moisturizing Shampoo 33.8 oz | $1,466.20 | above range | $21.89 | comparable item: Sebastian Drench Moisturizing Shampoo 33.8 oz (Pac |
| Premium Beauty | 905354975 WS 36 Magnifying Makeup Mirror in Matte White | $1,414.00 | above range | $844.44 | comparable item: WS 91WR Magnifying Makeup Mirror in Matte White |
| Premium Beauty | 300420575 Chi Iron Professional Display | $0.03 | below range | $57.00 | comparable item: Hot Tools Professional Flat Iron |
| Premium Beauty | 13473124207 GSI200WM Display | $0.01 | below range | $30.07 | median price of its category |
| Premium Beauty | 13512655387 GS13WM Display | $0.01 | below range | $30.07 | median price of its category |
| Premium Beauty | 13568805609 CHI STEAMPRESS DISPLAY | $0.01 | below range | $30.07 | median price of its category |
| Premium Beauty | 14619963568 new display | $0.01 | below range | $9.96 | comparable item: Nanette Lepore New |
| Seasonal | 108975112 Celebrations Lrg Shp Valentine's Day Marquee | $0.05 | below range | $5.76 | comparable item: Celebrations Shp Happy Valentine's Day |
| Seasonal | 339211939 1Strand Painted Glass Round Bead Strands Baking Paint Light Green 6mm  | $0.01 | below range | $10.24 | median price of the same kind of item |
| Toys | 47222329 Buzz Bee Walking Dead Abraham's M16 Blaster Bundle with 14 Ultra Tek L | $0.04 | below range | $6.93 | comparable item: Buzz Bee Toys Air Warriors 20 Count Ultra-Tek Dart |
| Toys | 187019861 One Direction Micro Assortment | $0.03 | below range | $50.48 | comparable item: Fortnite Micro Squad Mode 4- Pack Assortment |
| Toys | 411336022 Cs6124 Vtech Display | $0.03 | below range | $23.99 | median price of the same kind of item |
| Toys | 447202812 Cd1153 Vtech Display | $0.03 | below range | $23.99 | median price of the same kind of item |
| Toys | 827324690 Display Razor Rampage E100 Blue Elec Sct | $0.03 | below range | $97.69 | comparable item: Razor Black Label E90 Pk Elec Sct |
| Toys | 843382779 Cs6919-2 Vtech Display | $0.03 | below range | $23.99 | median price of the same kind of item |
| Toys | 14170354542 D72 Fall-2024 Apple iPad EOTF Table Signing Kit | $0.03 | below range | $17.69 | median price of the same kind of item |
| Toys | 10759933 Polly Pocket Pop n' Swap | $0.02 | below range | $22.88 | comparable item: Polly Pocket Pop 'N Swap Fashion Frenzy - Dance |
| Toys | 11331753 G.I. Joe Comic Book Duke | $0.01 | below range | $9.97 | comparable item: B/W Comic Book Leonardo |
| Toys | 121263808 Disney Pixar Onward Figure Assortment | $0.01 | below range | $13.82 | comparable item: Disney Toy Story 2" Figure 5-Pack Assortment |
| Toys | 129578759 Display - Pay Doh Dump Bin | $0.01 | below range | $14.83 | median price of its category |
| Toys | 144285250 Shop All Toys | $0.01 | below range | $8.88 | comparable item: L.O.L. Surprise! Shop |
| Toys | 155264727 Display 12v Yamaha Raptor Atv | $0.01 | below range | $17.99 | median price of its category |
| Toys | 155402341 Display Monster Jam Grave Digger Replica | $0.01 | below range | $9.57 | comparable item: Hot Wheels Monster Jam 1:64 Grave Digger |
| Toys | 155635979 Disney 24V Cinderella Carriage Powered Ride-On | $0.01 | below range | $59.87 | comparable item: Disney Cinderella 6volt Quad Ride-on |
| Toys | 164428934 Display 24v Halo Warthog | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 169312843 6v Disney Princess Convertible Display | $0.01 | below range | $21.56 | comparable item: VTech Disney Princess |
| Toys | 169525037 Disney - Disney Ec-1415, 12v New Frozen Suv | $0.01 | below range | $99.00 | comparable item: 6v Disney Frozen 3whl Scooter |
| Toys | 207626740 Vtech Display,leapster Explorer Gaming Pop Dis | $0.01 | below range | $23.99 | median price of the same kind of item |
| Toys | 210771956 Fisher Price Power Wheels Dune Racer Extreme Display | $0.01 | below range | $5.70 | comparable item: Fisher-Price Little People Wheelies Dune Racer |
| Toys | 229077082 Disney Princess 6v Mercedes Princess Display | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 242516906 John Deere Peg Perego Display Jd Gator Xuv | $0.01 | below range | $29.99 | comparable item: JOHN DEERE 825I XUV GATOR 1:16 Scale |
| Toys | 283892544 Play-Doh In Line Header | $0.01 | below range | $12.49 | median price of the same kind of item |
| Toys | 312401359 Leap Frog Gaming Display - Leappad | $0.01 | below range | $8.49 | comparable item: LEAP FROG |
| Toys | 346547821 Magic Bullet Compact Display | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 363191158 Leap Frog Gaming Display - Explorer | $0.01 | below range | $8.49 | comparable item: LEAP FROG |
| Toys | 380796234 Display Rollplay 6v Ice Cream Truck | $0.01 | below range | $32.80 | comparable item: Kinetic Sand Ice Cream Truck with 8oz of Kinetic S |
| Toys | 384293152 Monster Jam Dtr Display El Toro Monster Truck | $0.01 | below range | $77.00 | comparable item: 6V El Toro Loco Monster Jam Monster Truck Powered  |
| Toys | 404564191 WMT.com Preorder Dummy UPC 18 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 407360574 DISPLAY, 12V Corvette C8 Red | $0.01 | below range | $19.97 | comparable item: 1:16 Rc Corvette, Red |
| Toys | 424784763 Spiderman-marvel 6v Spiderman Supercar Display | $0.01 | below range | $10.77 | comparable item: Spiderman-marvel Spiderman 2099 |
| Toys | 482452628 Fisher Price Display - Power Wheels Corvette 6v | $0.01 | below range | $19.62 | comparable item: Fisher Price - Thomas & |
| Toys | 501604890 Display Honda Talon | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 504300875 Hasbro Avenger Marvel Header | $0.01 | below range | $5.21 | comparable item: Hot Wheels Marvel Avenger Assortment |
| Toys | 520401726 Phillips Philips1; Wake-up Disp2 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 528129293 WMT.com Preorder Dummy UPC 11 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 535126253 Hot Wheels 1980 Dodge Macho Power Wagon Vehicle | $0.01 | below range | $12.10 | comparable item: Hot Wheels 80 Dodge Macho Power Wagon |
| Toys | 548335956 Leap Frog Display,leapster Explorer | $0.01 | below range | $35.00 | comparable item: Leap Frog Leapster Explorer Pet Pals 2 |
| Toys | 605718594 Disney Pixar Cars Golden Diecast Lightning Mcqueen Car Play Vehicle | $0.01 | below range | $6.42 | comparable item: Disney Pixar Cars Cruisin' Lightning McQueen Car P |
| Toys | 622673715 Display Razor Pc100 Bl Aluminum Deck | $0.01 | below range | $39.93 | median price of the same kind of item |
| Toys | 645304174 Minnie Mouse Display 12v Minnie Mercedes | $0.01 | below range | $17.99 | median price of its category |
| Toys | 652566493 6V MINNIE CONVERTIBLE 2021 - DISPLAY SAMPLE | $0.01 | below range | $17.99 | median price of its category |
| Toys | 662328343 WMT.com Preorder Dummy UPC 46 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 709476318 Fisher Price Display - 12v Power Wheels Wild Thing | $0.01 | below range | $438.12 | comparable item: Fisher Price - Power Wheels Barbie Kfx |
| Toys | 711244049 Fisher Price Display 12v Barbie Camper | $0.01 | below range | $14.36 | median price of the same kind of item |
| Toys | 769136194 Display 12v Minnie Mouse Mercedes | $0.01 | below range | $17.99 | median price of its category |
| Toys | 800900485 WMT.com Preorder Dummy UPC 35 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 824439330 Display Razor Black Label E90 Electric S | $0.01 | below range | $93.72 | comparable item: Razor Black Label 3.0 Scooter |
| Toys | 836692286 DISPLAY 6V SPIDER-MAN SUPERCAR | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 865123594 Display Pulse Burner Pro Plus Scooter | $0.01 | below range | $21.55 | comparable item: Pulse Performance Products Burner Pro Plus Freesty |
| Toys | 867705443 Display 24v Disney Princess Carriage | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 874747398 Display 6v Bmw I8 Concept Car | $0.01 | below range | $13.69 | comparable item: Lexus 1:24 Futuristic Concept Car |
| Toys | 884511806 Fisher Price Displayer For Fjj63 F-150 Raptor Extreme | $0.01 | below range | $14.34 | comparable item: Fisher-Price Imaginext Raptor |
| Toys | 966008563 DISPLAY, 12V Ford F-150 Raptor, GRAY | $0.01 | below range | $17.99 | median price of its category |
| Toys | 1075899990 TINY LOVE 4-in-1 MAC, Tiny Farmland DISPLAY DNP | $0.01 | below range | $17.99 | median price of its category |
| Toys | 1536867174 Power Wheels Jurassic World Dino Racer Display | $0.01 | below range | $249.00 | comparable item: Power Wheels Jurassic World Dino Racer 12V Ride On |
| Toys | 1983991300 Power Wheels 12V Rubicorn Display | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 2092777007 Power Wheels 6V Jeep F23 Display | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 2172002708 Display Razor IconBL | $0.01 | below range | $39.93 | median price of the same kind of item |
| Toys | 2739531764 Display Razor RAMB16 | $0.01 | below range | $39.93 | median price of the same kind of item |
| Toys | 2744944254 Power Wheels 12V Jeep F23 Display | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 2820939560 DISPLAY Jetson Ryder PRO E-Scooter | $0.01 | below range | $49.99 | comparable item: Radio Flyer Pro Flyer Scooter |
| Toys | 5113283045 MONSTER FLAT DISPLAY | $0.01 | below range | $0.98 | comparable item: ARKITEC DISPLAY |
| Toys | 5310933881 John Deere Ground Force Display | $0.01 | below range | $31.56 | comparable item: John Deere Ground Force Mobile Play Set |
| Toys | 5318328719 Trend Pod Header - DAP 4695 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 5395277713 DISPLAY PW BARB JEEP | $0.01 | below range | $17.99 | median price of its category |
| Toys | 5493850395 24V RAZOR DIRT QUAD Display | $0.01 | below range | $39.93 | median price of the same kind of item |
| Toys | 5493876579 Creator Model Box 6517380 | $0.01 | below range | $9.99 | comparable item: LEGO Creator Snowman 30645 |
| Toys | 5495392041 Gaming Model Box 6517385 | $0.01 | below range | $20.48 | comparable item: DC GAMING |
| Toys | 7775111063 October Trend Pod Header - DAP 5112 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 11143969653 Disney Jr signage kit | $0.01 | below range | $17.99 | median price of its category |
| Toys | 14233309581 WMT Jan 2025 Header - DAP 5385 | $0.01 | below range | $17.99 | median price of its category |
| Toys | 19401313633 Power Wheels Dune Racer Dummy Display | $0.01 | below range | $69.47 | comparable item: Power Wheels Lil Dune Racer, 6V |
| Toys | 19874207065 PD NONSALEABLE DUMP BIN - EMPTY | $0.01 | below range | $17.99 | median price of its category |

## Placeholder listings (19831): barcode lookup only, not in typed search
Names that identify no product ("Merchandise", a brand alone, "Discontinued", "coming soon", a supplier code); kept so a scan of the barcode still prices the item, named from another listing with the same UPC or Open Facts when possible. Test listings and store displays are not carried (rejects above). Names filled: {'none': 19516, 'open_facts': 294, 'walmart_listing': 153}. First examples:
- 1573765 UPC 00213573504404 Food: Merchandise -> (name not provided) ($31.49)
- 3476499 UPC 00634904016029 Food: LOST HORIZONS -> (name not provided) ($23.66)
- 10292797 UPC 00044000012724 Food: Kraft Foods Merchandise -> (name not provided) ($6.82)
- 10292816 UPC 00044000015176 Food: Merchandise -> (name not provided) ($6.86)
- 10294394 UPC 00759283020167 Food: Merchandise -> (name not provided) ($30.0)
- 10295494 UPC 00022400000084 Food: MRS. DASH -> Mrs dash ($6.25)
- 10295495 UPC 00022400000107 Food: MRS. DASH -> Extra Spicy Seasoning Blend ($2.94)
- 10295500 UPC 00022400000619 Food: MRS. DASH -> (name not provided) ($2.94)
- 10295504 UPC 00022400000886 Food: MRS. DASH -> (name not provided) ($2.94)
- 10295505 UPC 00022400000992 Food: MRS. DASH -> (name not provided) ($2.94)
- 10307609 UPC 00041000301810 Food: WESTERN -> Wish-bone, western, the original sweet & smooth dressing ($3.42)
- 10308662 UPC 00067312002177 Food: Merchandise -> (name not provided) ($2.48)
- 10312916 UPC 00047900131212 Food: coming soon -> (name not provided) ($10.03)
- 10313308 UPC 00042743230504 Food: DICED PEACHES, DICED PEARS, WATER, GRAPES, CORN SYRUP, PINEAPPLE CHUNKS, SUGAR AND HALVED CHERRIES ARTIFICIALLY COLORED RED. -> Fruit Cocktail In  Heavy Syrup ($3.22)
- 10318121 UPC 00011300491580 Food: Merchandise -> (name not provided) ($3.49)

## Category labels in the sample review: 7.0% judged wrong
- 108546763: School, Office & Crafts -> Seasonal & Party
- 174947930: School, Office & Crafts -> Seasonal & Party
- 270653929: School, Office & Crafts -> Seasonal & Party
- 10292235: Pasta, Rice & Dry Goods -> Baking, Spices & Oils
- 9730183: Pasta, Rice & Dry Goods -> Baking, Spices & Oils
- 11090135: Beverages -> Health & Medicine
- 20626264979: School, Office & Crafts -> Household Supplies
- 21452180: Household Supplies -> School, Office & Crafts
- 47217200: Personal Care -> School, Office & Crafts
- 15849810524: Sports & Outdoors -> Kitchen & Dining
- 159394021: Sports & Outdoors -> Kitchen & Dining
- 670391086: Sports & Outdoors -> Kitchen & Dining
- 16308373080: Sports & Outdoors -> Kitchen & Dining
- 317462910: Sports & Outdoors -> Toys, Books & Games
- 52417366: Pet Food & Supplies -> Seasonal & Party
- 658793198: Lawn, Garden & Floral -> Toys, Books & Games
- 833655832: Household Supplies -> Electronics
- 915566502: Kitchen & Dining -> Home
- 1298999384: Household Supplies -> Seasonal & Party
- 697672975: Household Supplies -> Seasonal & Party
- 974787638: Hardware & Tools -> Household Supplies

## Live price differences (worst 25 of 500 checked)
- 15486201512 Hudson Baby Unisex Baby Cotton Poly Animal Face Hooded Towel, Pink Flamingo, One Size: snapshot 25.99 -> live not found
- 5400456211 (2 pack) Vibrant Life Jumbo Deodorizing Wipes for Dogs & Puppies, Vanilla Coconut, 100 Count: snapshot 15.95 -> live not found
- 18482659001 (5 pack) Vibrant Life Pine Wood Pet Bedding, 141 L Bag: snapshot 34.28 -> live not found
- 20060222813 3-Piece Reversible King Bedspread Set, Blue Geometric Mosaic Bedding Coverlet: snapshot 18.99 -> live not found
- 377955024 Goody Mosaic Natural Edge Control Hairbrush (Pack of 2): snapshot 4.94 -> live not found
- 13843116303 DecMode 18" Black Leather Handmade Box Style Magazine Holder with Detail Stitching and Curved Buckle Handles: snapshot 72.8 -> live not found
- 47220328 Windsoft Facial Quality Two-Ply Toilet Tissue, Bundle of 2: snapshot 32.46 -> live not found
- 612797452 Pet Life ® 'Bryer' 2-in-1 Hand-Inserted Microfiber Pet Grooming Towel and Brush: snapshot 15.99 -> live not found
- 256733949 Winter Holiday White Poodle Dish Drying Mat: snapshot 16.07 -> live not found
- 817904021 Simply Daisy Classic Monogram 28 x 36 in M Laundry Bag: snapshot 43.75 -> live not found
- 911164565 Simply Daisy Advent Calendar 18 x 29 in Green Laundry Bag: snapshot 31.25 -> live not found
- 14952507426 (4 pack) Mainstays Performance Cotton Washcloth, White, 12 in x 12 in, 1 Piece: snapshot 7.88 -> live not found
- 1496472722 Simply Daisy 16" x 16" Patterned Pumpkins Indoor/Outdoor Polyester Throw Pillow, Sienna: snapshot 34.99 -> live not found
- 530040089 Tan Goldendoodle Christmas Tree Dish Drying Mat: snapshot 16.8 -> live not found
- 19658070406 Charleston Woven Cotton Rich Tablecloth 60"X120" in Ash Blue: snapshot 25.0 -> live not found
- 843666090 Love Beauty and Planet—less plastic, more love.: snapshot 6.94 -> live not found
- 447536411 Giddyup! Buck's Decorative Tumbled Chips, 1 Bag: snapshot 17.89 -> live not found
- 971673403 Simply Daisy's Sunset Tulip Stripe 26 inch Blue Decorative Floral Throw Pillow: snapshot 60.0 -> live not found
- 5177096172 Carolines Treasures DAC4035PTHD 7.5 x 7.5 in. Unisex Hippie Animal Raccoon Pair of Pot Holders: snapshot 21.41 -> live not found
- 983934831 20 x 20 Inch Green Geometric Print Decorative Polyester Throw Pillow with a Linen Texture: snapshot 39.75 -> live not found
- 18593964616 Brentwood 80-Watt 1-Speed Electric Citrus Juicer with Ergonomic Lever, Black: snapshot 49.95 -> live not found
- 47213601 Avery Heavy-Duty View Binder with 2" One Touch EZD Ring 79802, Navy Blue and Avery Lay Flat View Report Cover w/Flexible Fastener, Letter-Size, 1/2" Capacity, Available in Multiple Colors Bundle: snapshot 16.21 -> live not found
- 1760743713 Simply Daisy 18" x 18" Spooky Cats Indoor/Outdoor Polyester Throw Pillow, Amethyst: snapshot 38.99 -> live not found
- 962471817 Simply Daisy Modern Monogram 28 x 36 inch x Laundry Bag: snapshot 43.75 -> live not found
- 53322235 Simply Daisy 16" x 16" Geometric Decorative Pillow: snapshot 17.42 -> live not found

## Unit-price outliers (worst 25)
- 14237731 FRONTLINE Plus for Dogs: 686.6667/fl oz vs median 0.0152 (x45175.440789), cat 19
- 1235174081 FunPillow Dumpbin 2G: 20051.0638/oz vs median 0.4915 (x40795.653713), cat 19
- 16439955 FRONTLINE Plus for Dogs: 614.0/fl oz vs median 0.0152 (x40394.736842), cat 19
- 1390264874 FLUZONE QIV 0.5ML: 6952.6627/fl oz vs median 0.2077 (x33474.543572), cat 14
- 16439958 FRONTLINE Plus for Dogs: 457.3333/fl oz vs median 0.0152 (x30087.717105), cat 19
- 325874115 TimeMist Settings Fragrance Dispenser Black 3 2/5"W x 3 2/5"D x 8 1/4"H 1047811EA: 0.0001/ct vs median 2.5 (x4e-05), cat 30
- 15557056882 HYRIMOZ 0.2ML B 20MG: 95588.2353/fl oz vs median 4.6372 (x20613.351872), cat 14
- 779549756 Taylor Precision Products 55814072F 400lb-capacity Digital Glass Body Analyzer & UPG AAA 50 Pack: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 27
- 940971158 Taylor Precision Products 55804072F 440lb-capacity Digital Glass Body Analyzer & UPG AAA 50 Pack: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 27
- 1432550670 BENTISM Rubber Curb Ramp Driveway Ramp for Curb 4.25" Rise 19.7" Wide 33069 lbs: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 1915291114 BENTISM Rubber Curb Ramp Driveway Ramp for Curb 3.7" Rise 39.4" Wide 33069lbs Load: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 2984313755 BENTISM Curb Ramp Rubber Driveway Ramp 2.6" Rise 15 tons Capacity Threshold Ramp: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 3084973264 BENTISM Rubber Curb Ramp Driveway Ramp for Curb 6" Rise 19.3" Wide 33069 lbs Load: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 3992026852 VEVOR Rubber Curb Ramp Driveway Ramp for Curb 2 Pack 6" Rise 19.3" Wide 33069lbs: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 5550793769 KFFKFF Rubber Threshold Ramp Door Ramp 3" Rise 33069 lbs Load Rubber Curb Ramp: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 5729715760 KFFKFF Rubber Threshold Ramp Door Ramp 1" Rise 33069 lbs Load Rubber Curb Ramp: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 14336422198 KFFKFF Enhanced Rubber Incline Ramp, 4" Height Doorway Ramp with Single Channel, Pure Rubber Vehicle Ramp with Anti-Slip Grainy Surface, 33069 lbs Weight Tolerance Sidewalk Ramp for Wheelchair: 0.0001/oz vs median 1.6425 (x6.1e-05), cat 14
- 34052351 Baseline Tactile monofilament evaluator, 1.65 (0.008 gram) Semmes-Weinstein: 65200.0/oz vs median 4.0985 (x15908.065047), cat 14
- 16622243 OFF! Clip-On Mosquito Repellent Starter Kit 0.0016 Ounces: 10706.25/oz vs median 0.6993 (x15309.95281), cat 16
- 38056035 Enfamil Human Milk Fortifier - 0.71g Foi: 5035.2/oz vs median 0.4349 (x11577.833985), cat 2
- 15539071805 (3 pack) Vicks VapoInhaler, Soothing Non-Medicated Vapor Inhaler with Menthol Scent, 2 Count: 17602.9412/fl oz vs median 1.8325 (x9605.970641), cat 14
- 1390510331 Splenda® No Calorie Sweetener Packets, 0.035 Oz Packets, 400/box, 6 Boxes/carton: 3942.8571/oz vs median 0.4331 (x9102.752164), cat 28
- 16553034 OFF! Clip-On Mosquito Repellent Starter Kit, 0.0016 oz: 5456.25/oz vs median 0.6993 (x7802.445302), cat 16
- 271852298 Freshwater Eco-Balance (480 gal): 0.0001/fl oz vs median 0.6577 (x0.000152), cat 19
- 685883525 Reef Re-Fresh (480 gal): 0.0001/fl oz vs median 0.6577 (x0.000152), cat 19
