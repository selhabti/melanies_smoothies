import streamlit as st
from snowflake.snowpark.functions import col
import requests
import pandas as pd

# Write directly to the app
st.title(":cup_with_straw: Customize Your Smoothie :cup_with_straw:")
st.write("Choose the fruits you want in your custom Smoothie")

# Get name for the order
name_on_order = st.text_input("Name on Smoothie")
st.write("The name on your Smoothie will be:", name_on_order)

# Get Snowflake session
cnx = st.connection("snowflake")
session = cnx.session()

# Get fruit options from Snowflake, including the SEARCH_ON column
try:
  fruit_options_df = session.table("SMOOTHIES.PUBLIC.FRUIT_OPTIONS").select(col('FRUIT_NAME'), col('SEARCH_ON')).to_pandas()
  st.dataframe(data=fruit_options_df, use_container_width=True)
except Exception as e:
  st.error(f"Failed to fetch fruit options: {str(e)}")

# Let user select fruits using the SEARCH_ON column for API calls
ingredients_list = st.multiselect(
  'Choose up to 5 ingredients:',
  fruit_options_df['FRUIT_NAME'].tolist() if not fruit_options_df.empty else [],
  max_selections=5
)

if ingredients_list:
  ingredients_string = ', '.join(ingredients_list)
  st.write(f"You chose: {ingredients_string}")
  
  time_to_insert = st.button('Submit Order')
  
  if time_to_insert:
      try:
          # Use parameterized query to prevent SQL injection
          session.sql(
              "INSERT INTO smoothies.public.orders(ingredients, name_on_order) VALUES (?, ?)",
              [ingredients_string, name_on_order]
          ).collect()
          st.success('Your Smoothie is ordered!', icon="✅")
      except Exception as e:
          st.error(f"An error occurred: {str(e)}")

  # Fetch data from Fruityvice API for each ingredient
  for fruit in ingredients_list:
      try:
          # Find the corresponding SEARCH_ON value for the selected fruit
          search_on_value = fruit_options_df.loc[fruit_options_df['FRUIT_NAME'] == fruit, 'SEARCH_ON'].values[0]
          fruityvice_response = requests.get(f"https://fruityvice.com/api/fruit/{search_on_value.lower()}")
          fruityvice_response.raise_for_status()  # Raise an error for bad responses
          fv_data = fruityvice_response.json()
          fv_df = pd.json_normalize(fv_data)  # Normalize JSON data into a flat table
          st.write(f"Nutrition information for {fruit}:")
          st.dataframe(data=fv_df, use_container_width=True)
      except requests.exceptions.HTTPError:
          st.write(f"Nutrition information for {fruit}:")
          not_found_df = pd.DataFrame({'Fruit': [fruit], 'Status': ['Not Found']})
          st.dataframe(data=not_found_df, use_container_width=True)
      except Exception as e:
          st.error(f"Failed to fetch data for {fruit}: {str(e)}")
