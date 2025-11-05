import polars as pl
import glob
import requests
import sys # sys.exit()

# Notes
# ---------------------------------------------------------------
# This script assumes selling items on TP by placing offer,
# NOT INSTANT SELL.
#
# Use Nexus plugin "GW2DRF" and BlishHud plugin "Farming Tracker" 
# to collect data.
#
# legend:
# Piece of Common Unidentified Gear -   BLU-UNID
# Piece of Unidentified Gear -          GRN-UNID
# Piece of Rare Unidentified Gear -     YEL-UNID
#
# Copper-Fed Salvage-o-Matic -          CF
# Runecrafter's Salvage-o-Matic -       RC
# Silver-Fed Salvage-o-Matic -          SF
# Black Lion Salvage Kit -              BL
#
# Fine gear -                           BLU-GEAR
# Masterwork gear -                     GRN-GEAR
# Rare gear -                           YEL_GEAR
# Exotic gear -                         ORG_GEAR
#
# Open -                                OPN
# Salvage -                             SLV
#
# Example:
# GRN-UNID_OPN_GRN-GEAR_SLV_RC -
# Open Piece of Unidentified Gear
# and salvage masterwork gear with Runecrafter's Salvage-o-Matic,
# don't touch rare or exotic gear, collect data.


# Steps - Open green unids, salvage green gear:
# 0. Clean up inventory (runecrafter will salvage blue items!)
# 1. Farming tracker reset
# 2. open green unids
# 3. salvage green gear with runecrafter
# 4. export CSV
# 5. add prefix to the CSV file - GRN-UNID_OPN_GRN-GEAR_SLV_RC_
# 6. Deposit materials / eat luck / cleanup

# Steps - Salvage yellow gear:
# 0. Clean up inventory
# 1. Farming tracker reset
# 2. salvage yellow gear with silver fed
# 3. export CSV
# 4. add prefix to the CSV file - YEL-GEAR_SLV_SF_
# 5. Deposit materials / eat luck / cleanup

# Steps - Salvage orange gear:
# 0. Clean up inventory
# 1. Farming tracker reset
# 2. salvage orange gear with Black Lion salvage kit
# 3. export CSV
# 4. add prefix to the CSV file - ORG-GEAR_SLV_BL_
# 5. Deposit materials / eat luck / cleanup

# Globals
# ---------------------------------------------------------------
# Directory containing the CSV files
DATA_DIR = "./opening_data"

# TP tax
TP_TAX = 0.85

# Data file prefixes
PREFIX_GRN_UNID_OPN_GRN_GEAR_SLV_RC = "GRN-UNID_OPN_GRN-GEAR_SLV_RC_"
PREFIX_YEL_GEAR_SLV_SF = "YEL-GEAR_SLV_SF_"
PREFIX_ORG_GEAR_SLV_BL = "ORG-GEAR_SLV_BL_"

# Farming plugin in GW2, exported data column names
CN_ITEM_ID = "item_id"
CN_ITEM_NAME = "item_name"
CN_ITEM_AMOUNT = "item_amount"
CN_CURRENCY_ID = "currency_id"
CN_CURRENCY_AMOUNT = "currency_amount"

# Items details column names 
CN_ITEM_TYPE = "item_type"
CN_ITEM_DETAIL_TYPE = "item_detail_type"
CN_ITEM_RARITY = "item_rarity"
CN_ITEM_BUY_PRICE = "item_buy_price"
CN_ITEM_SELL_PRICE = "item_sell_price"

# Calculated values column names
CN_ITEM_AVG_AMOUNT = "item_avg_amount"
CN_ITEM_VALUE = "item_value"    # represents final item value,
                                # in case of items to be sold on TP,
                                # the tax is included.
                                # In case of refinement materials,
                                # it has the best option (sell vs refine),
                                # in case of custom items (example: Luck),
                                # it has either constant value (salvage cost)
                                # or average value calculated from somewhere
                                # else (luck). It is a value per one item,
                                # "avg_amount" NOT included.
CN_TAX = "tax"
CN_PROFIT = "profit" # item_value * item_avg_amount
CN_PROFIT_250 = "profit_250" # item_value * item_avg_amount
CN_PRICE_AFTR_PROCESSING = "price_aftr_processing"
CN_TP_PRICE = "tp_price"
CN_CURRENT_BUY = "curr_buy"
CN_CURRENT_SELL = "curr_sell"

# Refinement DF column names
CN_BASE_ITEM = "base_item"
CN_BASE_ITEM_ID = "base_item_id"
CN_BASE_ITEM_SELL_PRICE = "base_item_sell_price"
CN_BASE_ITEM_QTY = "base_item_qty" # quantity required to craft refined version
CN_BASE_ITEM_QTY_SELL_PRICE = "base_item_qty_sell_price" # quantity * sell price
CN_RFNT_ITEM = "rfnt_item"
CN_RFNT_ITEM_ID = "rfnt_item_id"
CN_RFNT_ITEM_SELL_PRICE = "rfnt_item_sell_price"
CN_SELL_OR_REFINE = "sell_or_refine"
CN_ITEM_SELL_PRICE_AFTER_RFNT = "item_sell_price_after_rfnt"

# Custom items names
CUSTOM_ITEM_GRN_GEAR = "Green Gear"
CUSTOM_ITEM_YEL_GEAR = "Yellow Gear"
CUSTOM_ITEM_ORG_GEAR = "Orange Gear"
CUSTOM_ITEM_LUCK = "Luck"
CUSTOM_ITEM_SALVAGE = "Salvage"

# GW2 API link
URL_ITEMS_DETAILS = 'https://api.guildwars2.com/v2/items'
URL_ITEMS_TP = 'https://api.guildwars2.com/v2/commerce/prices'
API_REQUEST_SIZE_LIMIT = 200

# Salvage device cost per usage
SLV_COST_RC = 30
SLV_COST_SF = 60
SLV_COST_BL = 0

# Luck value
LUCK_VAL_FINE = 10 
LUCK_VAL_MASTERWORK = 50
LUCK_VAL_RARE = 100
LUCK_VAL_EXOTIC = 200
LUCK_VAL_LEGENDARY = 500

# Luck IDs
ITEM_ID_LUCK_FINE = 45175
ITEM_ID_LUCK_MASTERWORK = 45176
ITEM_ID_LUCK_RARE = 45177
ITEM_ID_LUCK_EXOTIC = 45178
ITEM_ID_LUCK_LEGENDARY = 45179

# Unidentify gear IDs
ITEM_ID_GREEN_UNID_GEAR = 84731

# Salvage tools IDs
ITEM_ID_SLV_BLACK_LION_1 = 19986
ITEM_ID_SLV_BLACK_LION_2 = 64195
ITEM_ID_SLV_BLACK_LION_3 = 67283

# Refinement items IDs
ITEM_ID_SILK_SCRAP = 19748
ITEM_ID_GOSSAMER_SCRAP = 19745
ITEM_ID_THICK_LEATHER_SECTION = 19729
ITEM_ID_HARDENED_LEATHER_SECTION = 19732
ITEM_ID_MITHRIL_ORE = 19700
ITEM_ID_ORICHALCUM_ORE = 19701
ITEM_ID_ELDER_WOOD_LOG = 19722
ITEM_ID_ANCIENT_WOOD_LOG = 19725
ITEM_ID_LUCENT_MOTE = 89140

ITEM_ID_BOLT_OF_SILK = 19747
ITEM_ID_BOLT_OF_GOSSAMER = 19746
ITEM_ID_CURED_THICK_LEATHER_SQUARE = 19735
ITEM_ID_CURED_HARDENED_LEATHER_SQUARE = 19737 
ITEM_ID_MITHRIL_INGOT = 19684
ITEM_ID_ORICHALCUM_INGOT = 19685
ITEM_ID_ELDER_WOOD_PLANK = 19709
ITEM_ID_ANCIENT_WOOD_PLANK = 19712
ITEM_ID_PILE_OF_LUCENT_CRYSTAL = 89271

# List with all refinement related items
REFINEMENT_ITEMS = [
    ITEM_ID_SILK_SCRAP,
    ITEM_ID_GOSSAMER_SCRAP,
    ITEM_ID_THICK_LEATHER_SECTION,
    ITEM_ID_HARDENED_LEATHER_SECTION,
    ITEM_ID_MITHRIL_ORE,
    ITEM_ID_ORICHALCUM_ORE,
    ITEM_ID_ELDER_WOOD_LOG,
    ITEM_ID_ANCIENT_WOOD_LOG,
    ITEM_ID_LUCENT_MOTE,
    ITEM_ID_BOLT_OF_SILK,
    ITEM_ID_BOLT_OF_GOSSAMER,
    ITEM_ID_CURED_THICK_LEATHER_SQUARE,
    ITEM_ID_CURED_HARDENED_LEATHER_SQUARE,
    ITEM_ID_MITHRIL_INGOT,
    ITEM_ID_ORICHALCUM_INGOT,
    ITEM_ID_ELDER_WOOD_PLANK,
    ITEM_ID_ANCIENT_WOOD_PLANK,
    ITEM_ID_PILE_OF_LUCENT_CRYSTAL,
]

# Setup and config stuff
# ---------------------------------------------------------------
def config_polars():
    pl.Config.set_tbl_cols(-1)
    pl.Config.set_tbl_rows(-1)
    pl.Config.set_fmt_str_lengths(2500)
    pl.Config.set_tbl_width_chars(2500)
    pl.Config.set_fmt_table_cell_list_len(10)
    # pl.Config.set_fmt_float("full")
    pl.Config.set_tbl_hide_column_data_types(True)
    pl.Config.set_tbl_hide_dataframe_shape(True)

# Load CSV files with opening data
# ---------------------------------------------------------------
def load_data_file(database_file_path):
    df = pl.read_csv(database_file_path, separator=",", infer_schema=False)
    df = df.cast({
        CN_ITEM_ID: pl.Int64,
        CN_ITEM_NAME: pl.String,
        CN_ITEM_AMOUNT: pl.Int64,
        CN_CURRENCY_ID: pl.Int64,
        CN_CURRENCY_AMOUNT: pl.Int64,
        })
    return df

# Load csv files with items after opening bags
def load_data(prefix):
    # Get list of all CSV files in the directory
    csv_files = glob.glob(f"{DATA_DIR}/{prefix}*.csv")

    if (not csv_files):
        sys.exit("No opening data files found!!!")
    
    print(f"{prefix} data files count: {len(csv_files)}")
    # print(f"Data files:")
    # print(*csv_files, sep='\n')

    df = pl.DataFrame()
    for f in csv_files:
        tmp = load_data_file(f)
        df = pl.concat([df, tmp])

    df = (df
        .drop(CN_CURRENCY_ID, CN_CURRENCY_AMOUNT)
        .sort(CN_ITEM_AMOUNT)
    )


    return df

# Various aggregations
# ---------------------------------------------------------------
# Aggregate duplicates in dataframe
def agg_duplicates(df):
    df = (df.group_by([CN_ITEM_ID, CN_ITEM_NAME])
        .agg(pl.sum(CN_ITEM_AMOUNT))
    )

    return df

def agg_yel_and_org_gear(df):
    yel_gear_count = (df.filter(
        ((pl.col(CN_ITEM_TYPE) == "Weapon") | (pl.col(CN_ITEM_TYPE) == "Armor"))
        &
        (pl.col(CN_ITEM_RARITY) == "Rare")
        )
        .select(pl.sum(CN_ITEM_AMOUNT))
        .item(0, CN_ITEM_AMOUNT)
        )

    org_gear_count = (df.filter(
        ((pl.col(CN_ITEM_TYPE) == "Weapon") | (pl.col(CN_ITEM_TYPE) == "Armor"))
        &
        (pl.col(CN_ITEM_RARITY) == "Exotic")
        )
        .select(pl.sum(CN_ITEM_AMOUNT))
        .item(0, CN_ITEM_AMOUNT)
        )

    df = (df.remove(
        ((pl.col(CN_ITEM_TYPE) == "Weapon") | (pl.col(CN_ITEM_TYPE) == "Armor"))
        &
        ((pl.col(CN_ITEM_RARITY) == "Rare") | (pl.col(CN_ITEM_RARITY) == "Exotic"))
        )
        .drop(CN_ITEM_TYPE)
        .drop(CN_ITEM_DETAIL_TYPE)
        .drop(CN_ITEM_RARITY)
        )

    # Extend main DF with aggregated amount of rares and exotics
    df = df.extend(pl.DataFrame({
        CN_ITEM_ID: [None, None],
        CN_ITEM_NAME: [CUSTOM_ITEM_YEL_GEAR, CUSTOM_ITEM_ORG_GEAR],
        CN_ITEM_AMOUNT: [yel_gear_count, org_gear_count]}))

    return df

# def agg_gear_data(df):

# Extract unidentify gear count
# ---------------------------------------------------------------
def get_opn_green_unid_count(df):
    df = df.filter(pl.col(CN_ITEM_ID) == ITEM_ID_GREEN_UNID_GEAR)

    if (df.is_empty()):
        sys.exit("Green unid not found in opened items dataframe!!!")

    green_unid_count = -(df.item(0, CN_ITEM_AMOUNT))
    return green_unid_count

# Get salvaged gear count
# ---------------------------------------------------------------
def get_slv_gear_count(df):
    gear_count = (-df.filter(
        (pl.col(CN_ITEM_AMOUNT) < 0) &
        (pl.col(CN_ITEM_ID) != ITEM_ID_SLV_BLACK_LION_1) &
        (pl.col(CN_ITEM_ID) != ITEM_ID_SLV_BLACK_LION_2) &
        (pl.col(CN_ITEM_ID) != ITEM_ID_SLV_BLACK_LION_3)
        )[CN_ITEM_AMOUNT].sum()
    )

    return gear_count

def remove_slv_gear(df):
    df = df.remove((pl.col(CN_ITEM_AMOUNT) < 0))
    return df

# Create main DF
# ---------------------------------------------------------------
def create_main_df(df, opn_grn_unid_count):
    yel_gear_count = (df.filter( pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_YEL_GEAR)
        .select(pl.sum(CN_ITEM_AMOUNT))
        .item(0, CN_ITEM_AMOUNT))

    org_gear_count = (df.filter( pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_ORG_GEAR)
        .select(pl.sum(CN_ITEM_AMOUNT))
        .item(0, CN_ITEM_AMOUNT))

    grn_gear_count = opn_grn_unid_count - yel_gear_count - org_gear_count

    df_main = (pl.DataFrame({
        CN_ITEM_NAME: [
            CUSTOM_ITEM_GRN_GEAR,
            CUSTOM_ITEM_YEL_GEAR,
            CUSTOM_ITEM_ORG_GEAR,
            ],
        CN_ITEM_AMOUNT: [
            grn_gear_count,
            yel_gear_count,
            org_gear_count,
        ]
    }))

    avg_amount = (pl.col(CN_ITEM_AMOUNT) / opn_grn_unid_count)
    df_main = (df_main
        .with_columns(avg_amount.alias(CN_ITEM_AVG_AMOUNT))
        .cast({CN_ITEM_AVG_AMOUNT: pl.Float64}))

    return df_main

# Create green gear salvage result DF
# ---------------------------------------------------------------
def create_grn_gear_slv(init_df):
    df = (init_df.remove(
        (pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_YEL_GEAR) |
        (pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_ORG_GEAR)
    ))

    return df

# RAW data initial cleanup
# ---------------------------------------------------------------
def remove_green_unids_row(df):
    df = df.remove(pl.col(CN_ITEM_ID) == ITEM_ID_GREEN_UNID_GEAR)

    tmp = df.filter(pl.col(CN_ITEM_AMOUNT) < 0)
    if (not tmp.is_empty()):
        sys.exit("There are more below zero 'item_amount' fields!!!")

    return df

# Get data from API
# ---------------------------------------------------------------
# Fetch items data from the Guild Wars 2 API for multiple item IDs
# and return a joined dataframe.
def add_items_details(df):
    item_ids = df.get_column(CN_ITEM_ID).drop_nulls()
    items_details = []

    while(item_ids.len() > 0):

        # Build comma-separated ID list with limit of 200 per request
        if (item_ids.len() <= API_REQUEST_SIZE_LIMIT):
            ids_param = ",".join(map(str, item_ids))
        else:
            ids_param = ",".join(map(str, item_ids[0:API_REQUEST_SIZE_LIMIT]))
        
        item_ids = item_ids[API_REQUEST_SIZE_LIMIT:]

        url = f"{URL_ITEMS_DETAILS}?ids={ids_param}"

        response = requests.get(url)
        response.raise_for_status()  # Throw error if something went wrong

        items_data = response.json()
        for item in items_data:
            items_details.append({
                CN_ITEM_ID: item.get("id"),
                CN_ITEM_TYPE: item.get("type"),
                CN_ITEM_DETAIL_TYPE: item.get("details", {}).get("type"),
                CN_ITEM_RARITY: item.get("rarity"),
            })

    items_details = pl.DataFrame(items_details)
    df = df.join(items_details, on=CN_ITEM_ID, coalesce=True)
    return df

# Fetch items TP prices from the Guild Wars 2 API for multiple item IDs
# and return a joined dataframe.
# Addional items are added manually as they are required later.
def get_tp_prices(item_ids):
    # Build comma-separated ID list
    ids_param = ",".join(map(str, item_ids))

    # Get TP prices
    url = f"{URL_ITEMS_TP}?ids={ids_param}"

    response = requests.get(url)
    response.raise_for_status()  # Throw error if something went wrong

    items_data = response.json()
    items_tp_prices = []

    for item in items_data:
        items_tp_prices.append({
            CN_ITEM_ID: item.get("id"),
            CN_ITEM_BUY_PRICE: item.get("buys", {}).get("unit_price"),
            CN_ITEM_SELL_PRICE: item.get("sells", {}).get("unit_price"),
        })

    items_tp_prices = pl.DataFrame(items_tp_prices).cast({
        CN_ITEM_BUY_PRICE: pl.Float64,
        CN_ITEM_SELL_PRICE: pl.Float64,
    })

    # Get names for above items
    url = f"{URL_ITEMS_DETAILS}?ids={ids_param}"

    response = requests.get(url)
    response.raise_for_status()  # Throw error if something went wrong

    items_data = response.json()
    items_names = []

    for item in items_data:
        items_names.append({
            CN_ITEM_ID: item.get("id"),
            CN_ITEM_NAME: item.get("name"),
        })

    items_names = pl.DataFrame(items_names)

    df_tp_prices = items_tp_prices.join(items_names, on=CN_ITEM_ID, coalesce=True)

    return df_tp_prices

# Refinement
# ---------------------------------------------------------------
def add_refinement_recipe(rfnt_df, df_tp, base_id, rfnt_id, base_qty):
    base = df_tp.filter(pl.col(CN_ITEM_ID) == base_id)
    rfnt = df_tp.filter(pl.col(CN_ITEM_ID) == rfnt_id)

    base_sell = base.item(0, CN_ITEM_SELL_PRICE)
    base_qty_sell_price = base_qty * base_sell

    rfnt_df = rfnt_df.extend(pl.DataFrame({
        CN_BASE_ITEM_ID: base_id,
        CN_RFNT_ITEM_ID: rfnt_id,
        CN_BASE_ITEM_SELL_PRICE: base_sell,
        CN_BASE_ITEM_QTY: base_qty,
        CN_BASE_ITEM: base.item(0, CN_ITEM_NAME),
        CN_RFNT_ITEM: rfnt.item(0, CN_ITEM_NAME),
        CN_BASE_ITEM_QTY_SELL_PRICE: base_qty_sell_price,
        CN_RFNT_ITEM_SELL_PRICE: rfnt.item(0, CN_ITEM_SELL_PRICE),
        }))

    return rfnt_df

def get_refinement_df(df_tp):
    df = pl.DataFrame({}, schema={
        CN_BASE_ITEM_ID: pl.Int64,
        CN_RFNT_ITEM_ID: pl.Int64,
        CN_BASE_ITEM_SELL_PRICE: pl.Float64,
        CN_BASE_ITEM_QTY: pl.Int64,
        CN_BASE_ITEM: pl.String,
        CN_RFNT_ITEM: pl.String,
        CN_BASE_ITEM_QTY_SELL_PRICE: pl.Float64,
        CN_RFNT_ITEM_SELL_PRICE: pl.Float64,
        })

    # Silk Scrap --> Bolt of Silk
    df = add_refinement_recipe(df, df_tp, ITEM_ID_SILK_SCRAP, ITEM_ID_BOLT_OF_SILK, 3)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_GOSSAMER_SCRAP, ITEM_ID_BOLT_OF_GOSSAMER, 2)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_THICK_LEATHER_SECTION, ITEM_ID_CURED_THICK_LEATHER_SQUARE, 4)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_HARDENED_LEATHER_SECTION, ITEM_ID_CURED_HARDENED_LEATHER_SQUARE, 3)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_MITHRIL_ORE, ITEM_ID_MITHRIL_INGOT, 2)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_ORICHALCUM_ORE, ITEM_ID_ORICHALCUM_INGOT, 2)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_ELDER_WOOD_LOG, ITEM_ID_ELDER_WOOD_PLANK, 3)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_ANCIENT_WOOD_LOG, ITEM_ID_ANCIENT_WOOD_PLANK, 3)
    df = add_refinement_recipe(df, df_tp, ITEM_ID_LUCENT_MOTE, ITEM_ID_PILE_OF_LUCENT_CRYSTAL, 10)

    sell_or_refine = (pl
        .when(pl.col(CN_RFNT_ITEM_SELL_PRICE) > pl.col(CN_BASE_ITEM_QTY_SELL_PRICE))
        .then(pl.lit("REFINE"))
        .otherwise(pl.lit("SELL"))
        .cast(pl.String)
        .alias(CN_SELL_OR_REFINE)
    )

    price_after_rfnt = (pl
        .when(pl.col(CN_RFNT_ITEM_SELL_PRICE) > pl.col(CN_BASE_ITEM_QTY_SELL_PRICE))
        .then((pl.col(CN_RFNT_ITEM_SELL_PRICE) / pl.col(CN_BASE_ITEM_QTY)))
        .otherwise(pl.col(CN_BASE_ITEM_SELL_PRICE))
        .cast(pl.Float64)
        .alias(CN_ITEM_SELL_PRICE_AFTER_RFNT)
    )

    df = df.with_columns(sell_or_refine, price_after_rfnt)
    return df

# Add columns
# ---------------------------------------------------------------
def add_empty_item_value(df):
    df = df.with_columns(pl
        .lit(None)
        .cast(pl.Float64)
        .alias(CN_ITEM_VALUE)
    )

    return df

# Add tp sell price, sell price after rfnt, tax and combine that into item value
def add_tp_prices(df, df_tp_prices, df_refinement):
    # add tp sell price
    df = df.join(
        df_tp_prices.select(CN_ITEM_ID, CN_ITEM_SELL_PRICE),
        on=CN_ITEM_ID,
        coalesce=True,
        how="left",
    )

    # add tp sell price after refinement
    df = df.join(
        df_refinement.select(CN_BASE_ITEM_ID, CN_ITEM_SELL_PRICE_AFTER_RFNT),
        left_on=CN_ITEM_ID,
        right_on=CN_BASE_ITEM_ID,
        how="left",
    )

    # add tax column
    tax = (pl
        .when(
            (pl.col(CN_ITEM_SELL_PRICE).is_not_null())
        )
        .then(pl.lit(TP_TAX))
        .otherwise(pl.lit(1))
        .cast(pl.Float64)
        .alias(CN_TAX)
    )
    df = df.with_columns(tax)

    # TODO: Optional:
    # Modify tax column to exclude items that I will store in 
    # material storage rather than selling on TP

    # combine above into item_value column
    item_value = (pl
        .when(pl.col(CN_ITEM_VALUE).is_not_null())
        .then(pl.col(CN_ITEM_VALUE))
        .when(pl.col(CN_ITEM_SELL_PRICE_AFTER_RFNT).is_not_null())
        .then(pl.col(CN_ITEM_SELL_PRICE_AFTER_RFNT))
        .when(pl.col(CN_ITEM_SELL_PRICE).is_not_null())
        .then(pl.col(CN_ITEM_SELL_PRICE))
        .otherwise(pl.lit(0))
        .mul(pl.col(CN_TAX))
        .alias(CN_ITEM_VALUE)
    )
    df = df.with_columns(item_value)

    # drop no longer needed columns
    df = (df
        .drop(CN_ITEM_SELL_PRICE)
        .drop(CN_ITEM_SELL_PRICE_AFTER_RFNT)
        .drop(CN_TAX)
    )

    return df

def add_item_avg_amount(df, gear_count):
    avg_amount = (pl.col(CN_ITEM_AMOUNT) / gear_count)
    df = (df
        .with_columns(avg_amount.alias(CN_ITEM_AVG_AMOUNT))
        .cast({CN_ITEM_AVG_AMOUNT: pl.Float64}))

    return df

# Add profit column (item_value * item_avg_amount)
def add_profit(df):
    df = df.with_columns(
        (pl.col(CN_ITEM_AVG_AMOUNT) * pl.col(CN_ITEM_VALUE))
        .alias(CN_PROFIT)
    )

    return df

# Add rows
# ---------------------------------------------------------------
def add_salvage_cost(df, slv_cost, slv_count):
    df = df.extend(pl.DataFrame({
        CN_ITEM_ID: None,
        CN_ITEM_NAME: CUSTOM_ITEM_SALVAGE,
        CN_ITEM_AMOUNT: slv_count,
        CN_ITEM_VALUE: -slv_cost,
        }, schema = {
        CN_ITEM_ID: pl.Int64,
        CN_ITEM_NAME: pl.String,
        CN_ITEM_AMOUNT: pl.Int64,
        CN_ITEM_VALUE: pl.Int64,
        CN_ITEM_VALUE: pl.Float64,
        })
    )

    return df

def add_aggregated_luck(df):
    luck = 0

    luck += (df.filter(pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_FINE)
             .select(pl.sum(CN_ITEM_AMOUNT))
             .item(0, CN_ITEM_AMOUNT) * LUCK_VAL_FINE
             )

    luck += (df.filter(pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_MASTERWORK)
             .select(pl.sum(CN_ITEM_AMOUNT))
             .item(0, CN_ITEM_AMOUNT) * LUCK_VAL_MASTERWORK
             )

    luck += (df.filter(pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_RARE)
             .select(pl.sum(CN_ITEM_AMOUNT))
             .item(0, CN_ITEM_AMOUNT) * LUCK_VAL_RARE
             )

    luck += (df.filter(pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_EXOTIC)
             .select(pl.sum(CN_ITEM_AMOUNT))
             .item(0, CN_ITEM_AMOUNT) * LUCK_VAL_EXOTIC
             )

    luck += (df.filter(pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_LEGENDARY)
             .select(pl.sum(CN_ITEM_AMOUNT))
             .item(0, CN_ITEM_AMOUNT) * LUCK_VAL_LEGENDARY
             )

    df = (df.remove(
        (pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_FINE) |
        (pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_MASTERWORK) |
        (pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_RARE) |
        (pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_EXOTIC) |
        (pl.col(CN_ITEM_ID) == ITEM_ID_LUCK_LEGENDARY)
    ))

    df = df.extend(pl.DataFrame({
        CN_ITEM_ID: None,
        CN_ITEM_NAME: CUSTOM_ITEM_LUCK,
        CN_ITEM_AMOUNT: luck,
        CN_ITEM_VALUE: None, # TODO: fix that with luck bags data
        }))

    return df

# ---------------------------------------------------------------
def get_summed_profit(df):
    return df[CN_PROFIT].sum()

# ---------------------------------------------------------------
def handle_main_df(df_main, df_grn_gear, df_yel_gear, df_org_gear):
    # Add item value column
    df_main = df_main.with_columns(pl
        .when(pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_GRN_GEAR)
        .then(get_summed_profit(df_grn_gear))
        .when(pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_YEL_GEAR)
        .then(get_summed_profit(df_yel_gear))
        .when(pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_ORG_GEAR)
        .then(get_summed_profit(df_org_gear))
        .otherwise(pl.lit(0))
        .alias(CN_ITEM_VALUE)
    )

    # Add profit column
    df_main = add_profit(df_main)

    return df_main

# ---------------------------------------------------------------
def create_buy_or_not_df(avg_profit_from_grn_unid, df_tp_prices):
    grn_unid_buy_price = (df_tp_prices
        .filter(pl.col(CN_ITEM_ID) == ITEM_ID_GREEN_UNID_GEAR)
        [CN_ITEM_BUY_PRICE].item())

    grn_unid_sell_price = (df_tp_prices
        .filter(pl.col(CN_ITEM_ID) == ITEM_ID_GREEN_UNID_GEAR)
        [CN_ITEM_SELL_PRICE].item())

    margin = 3
    range_a = grn_unid_buy_price - margin
    range_b = grn_unid_sell_price + margin + 1
    range_a = int(range_a)
    range_b = int(range_b)
    rows_to_show = range_b - range_a

    df_buy_or_not = pl.DataFrame({
        CN_ITEM_NAME: ["green unid"] * rows_to_show,
        CN_TP_PRICE: range(range_a, range_b),
        }, schema={
        CN_ITEM_NAME: pl.String,
        CN_TP_PRICE: pl.Int64,
        }
    )

    # add current tp buy price column
    df_buy_or_not = df_buy_or_not.with_columns(pl
        .when(pl.col(CN_TP_PRICE) == grn_unid_buy_price)
        .then(pl.lit("x"))
        .otherwise(pl.lit("-"))
        .cast(pl.String)
        .alias(CN_CURRENT_BUY)
    )

    # add current tp sell price column
    df_buy_or_not = df_buy_or_not.with_columns(pl
        .when(pl.col(CN_TP_PRICE) == grn_unid_sell_price)
        .then(pl.lit("x"))
        .otherwise(pl.lit("-"))
        .cast(pl.String)
        .alias(CN_CURRENT_SELL)
    )

    # add price after processing
    df_buy_or_not = df_buy_or_not.with_columns(pl
        .lit(avg_profit_from_grn_unid)
        .alias(CN_PRICE_AFTR_PROCESSING)
    )

    # add profit column
    df_buy_or_not = df_buy_or_not.with_columns(
        (pl.col(CN_PRICE_AFTR_PROCESSING) - pl.col(CN_TP_PRICE))
        .alias(CN_PROFIT)
    )

    df_buy_or_not = df_buy_or_not.with_columns(
        (pl.col(CN_PROFIT) * 250)
        .alias(CN_PROFIT_250)
    )

    return df_buy_or_not

# Main
# ---------------------------------------------------------------
if __name__ == "__main__":
    opn_grn_unid_count = 0
    grn_gear_count = 0
    yel_gear_count = 0
    org_gear_count = 0

    df_grn_opn_slv = pl.DataFrame()
    df_main = pl.DataFrame()
    df_grn_gear_slv_rc = pl.DataFrame()
    df_yel_gear_slv_sf = pl.DataFrame()
    df_org_gear_slv_bl = pl.DataFrame()
    df_tp_prices = pl.DataFrame()
    df_refinement = pl.DataFrame()
    df_buy_or_not = pl.DataFrame()

    config_polars()

    # ---------------------------------------------------------------
    # --- INITIAL DATA HANDLING
    # ---------------------------------------------------------------
    # --- Load and cleanup initial dataframe
    df_grn_opn_slv = load_data(PREFIX_GRN_UNID_OPN_GRN_GEAR_SLV_RC)
    df_grn_opn_slv = agg_duplicates(df_grn_opn_slv)
    opn_grn_unid_count = get_opn_green_unid_count(df_grn_opn_slv)

    df_grn_opn_slv = remove_green_unids_row(df_grn_opn_slv)

    # --- Aggregate yellow and orange gear
    df_grn_opn_slv = add_items_details(df_grn_opn_slv)
    df_grn_opn_slv = agg_yel_and_org_gear(df_grn_opn_slv)

    # --- Create main dataframe
    df_main = create_main_df(df_grn_opn_slv, opn_grn_unid_count)

    # ---------------------------------------------------------------
    # --- INITIAL GREEN GEAR DATA HANDLING
    # ---------------------------------------------------------------
    grn_gear_count = (df_main
        .filter(pl.col(CN_ITEM_NAME) == CUSTOM_ITEM_GRN_GEAR)
        .select(pl.sum(CN_ITEM_AMOUNT))
        .item(0, CN_ITEM_AMOUNT))
    df_grn_gear_slv_rc = create_grn_gear_slv(df_grn_opn_slv)

    # ---------------------------------------------------------------
    # --- INITIAL YELLOW GEAR DATA HANDLING
    # ---------------------------------------------------------------
    df_yel_gear_slv_sf = load_data(PREFIX_YEL_GEAR_SLV_SF)
    df_yel_gear_slv_sf = agg_duplicates(df_yel_gear_slv_sf)
    yel_gear_count = get_slv_gear_count(df_yel_gear_slv_sf)
    df_yel_gear_slv_sf = remove_slv_gear(df_yel_gear_slv_sf)

    # ---------------------------------------------------------------
    # --- INITIAL ORANGE GEAR DATA HANDLING
    # ---------------------------------------------------------------
    df_org_gear_slv_bl = load_data(PREFIX_ORG_GEAR_SLV_BL)
    df_org_gear_slv_bl = agg_duplicates(df_org_gear_slv_bl)
    org_gear_count = get_slv_gear_count(df_org_gear_slv_bl)
    df_org_gear_slv_bl = remove_slv_gear(df_org_gear_slv_bl)

    # ---------------------------------------------------------------
    # --- CREATE TP PRICES DF AND REFINEMENT DF
    # ---------------------------------------------------------------
    item_ids = (pl.concat([
        df_grn_gear_slv_rc[CN_ITEM_ID],
        df_yel_gear_slv_sf[CN_ITEM_ID],
        df_org_gear_slv_bl[CN_ITEM_ID],
        ])
        .append(pl.Series(CN_ITEM_ID, REFINEMENT_ITEMS))
        .append(pl.Series(CN_ITEM_ID, [ITEM_ID_GREEN_UNID_GEAR]))
        .unique()
    )
    df_tp_prices = get_tp_prices(item_ids)
    df_refinement = get_refinement_df(df_tp_prices)

    # ---------------------------------------------------------------
    # --- GREEN GEAR DATA HANDLING
    # ---------------------------------------------------------------
    df_grn_gear_slv_rc = add_empty_item_value(df_grn_gear_slv_rc)
    df_grn_gear_slv_rc = add_aggregated_luck(df_grn_gear_slv_rc)
    df_grn_gear_slv_rc = add_salvage_cost(df_grn_gear_slv_rc, SLV_COST_RC, grn_gear_count)
    df_grn_gear_slv_rc = add_item_avg_amount(df_grn_gear_slv_rc, grn_gear_count)
    df_grn_gear_slv_rc = add_tp_prices(df_grn_gear_slv_rc, df_tp_prices, df_refinement)
    df_grn_gear_slv_rc = add_profit(df_grn_gear_slv_rc)

    # ---------------------------------------------------------------
    # --- YELLOW GEAR DATA HANDLING
    # ---------------------------------------------------------------
    df_yel_gear_slv_sf = add_empty_item_value(df_yel_gear_slv_sf)
    df_yel_gear_slv_sf = add_aggregated_luck(df_yel_gear_slv_sf)
    df_yel_gear_slv_sf = add_salvage_cost(df_yel_gear_slv_sf, SLV_COST_SF, yel_gear_count)
    df_yel_gear_slv_sf = add_item_avg_amount(df_yel_gear_slv_sf, yel_gear_count)
    df_yel_gear_slv_sf = add_tp_prices(df_yel_gear_slv_sf, df_tp_prices, df_refinement)
    df_yel_gear_slv_sf = add_profit(df_yel_gear_slv_sf)

    # ---------------------------------------------------------------
    # --- ORANGE GEAR DATA HANDLING
    # ---------------------------------------------------------------
    df_org_gear_slv_bl = add_empty_item_value(df_org_gear_slv_bl)
    df_org_gear_slv_bl = add_aggregated_luck(df_org_gear_slv_bl)
    df_org_gear_slv_bl = add_salvage_cost(df_org_gear_slv_bl, SLV_COST_BL, org_gear_count)
    df_org_gear_slv_bl = add_item_avg_amount(df_org_gear_slv_bl, org_gear_count)
    df_org_gear_slv_bl = add_tp_prices(df_org_gear_slv_bl, df_tp_prices, df_refinement)
    df_org_gear_slv_bl = add_profit(df_org_gear_slv_bl)

    # ---------------------------------------------------------------
    # --- MAIN DF HANDLING
    # ---------------------------------------------------------------
    df_main = handle_main_df(df_main, df_grn_gear_slv_rc, df_yel_gear_slv_sf, df_org_gear_slv_bl)
    avg_profit = get_summed_profit(df_main)


    # ---------------------------------------------------------------
    # --- BUY OR NOT TABLE
    # ---------------------------------------------------------------
    df_buy_or_not = create_buy_or_not_df(avg_profit, df_tp_prices)

    # ---------------------------------------------------------------
    # --- FINAL REPORT
    # ---------------------------------------------------------------
    print(f"Opened green unid count: {opn_grn_unid_count}")
    print(f"Salvaged green gear count: {grn_gear_count}")
    print(f"Salvaged yellow gear count: {yel_gear_count}")
    print(f"Salvaged orange gear count: {org_gear_count}")
    print(f"Average profit from opening 1 green unid: {avg_profit}")

    # print(df_grn_gear_slv_rc.sort(CN_PROFIT))
    # print(df_yel_gear_slv_sf.sort(CN_PROFIT))
    # print(df_org_gear_slv_bl.sort(CN_PROFIT))

    print(df_main)
    print(df_refinement.drop(CN_BASE_ITEM_ID, CN_RFNT_ITEM_ID, CN_BASE_ITEM_SELL_PRICE, CN_BASE_ITEM_QTY))
    print(df_buy_or_not)