import streamlit as st
import pandas as pd
import os
import openai
from google.cloud import bigquery
import concurrent.futures
from streamlit.runtime.scriptrunner import add_script_run_ctx
import requests, json
from census import Census
from us import states

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
OpenAIKey = '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'


client_bq = bigquery.Client()

def get_query_year(prompt):
  response = client.chat.completions.create(
  model="gpt-3.5-turbo",
  temperature = 0,
  max_tokens = 50,
  messages=[
    {"role": "system", "content": "You are a year extraction agent. You respond only with a year given a prompt. If the prompt is 'how many ice cream bars were sold in 2015' you should respond only with '2015'. If the prompt is 'how many ice cream bars were sold between 2015 and 2018' you should respond only with '2015, 2018'. If no year is present in the prompt, respond with 'NA'"},
    {"role": "user", "content": f"Respond with the year(s) relevant to this prompt and do not include any other text: {prompt}."}
  ]
)
  raw = response.choices[0].message.content
  return raw

def scrub_prompt(prompt):
  response = client.chat.completions.create(
  model="gpt-4-turbo",
  temperature = 0,
  max_tokens = 50,
  messages=[
    {"role": "system", "content": "You are a year, weather, and economic removal agent. You remove references to years, weather, and economic indicators from the prompt. If the prompt is 'how many ice cream bars were sold in 2015?' you should respond with 'how many ice cream bars were sold?'. If the prompt is 'Which state has the most wildfires and what was it's unemployment rate in 2022?' you should respond with 'Which state has the most wildfires?'. Things like median income and maximum temperate are indicators and should be removed."},
      {"role": "user", "content": f"Prompt: {prompt}."}
    ]
  )
  raw = response.choices[0].message.content
  return raw


def gen_sql(prompt):
  response = client.chat.completions.create(
    model="gpt-4-turbo",
    temperature = 0,
    max_tokens = 50,
    messages=[
      {"role": "system", "content": "You are a column selecting agent. You respond only with a tab-separated list of column names that could help answer the prompt and nothing more. Include too many column names instead of too few."},
      {"role": "user", "content": f"Prompt: {prompt}, Column Options: OBJECTID, FOD_ID, FPA_ID, SOURCE_SYSTEM_TYPE, SOURCE_SYSTEM,NWCG_REPORTING_AGENCY, NWCG_REPORTING_UNIT_ID,NWCG_REPORTING_UNIT_NAME, SOURCE_REPORTING_UNIT,SOURCE_REPORTING_UNIT_NAME, LOCAL_FIRE_REPORT_ID,LOCAL_INCIDENT_ID, FIRE_CODE, FIRE_NAME,ICS_209_INCIDENT_NUMBER, ICS_209_NAME, MTBS_ID, MTBS_FIRE_NAME,COMPLEX_NAME, FIRE_YEAR, DISCOVERY_DATE, DISCOVERY_DOY,DISCOVERY_TIME, CONT_DATE,CONT_DOY, CONT_TIME, FIRE_SIZE, FIRE_SIZE_CLASS, LATITUDE,LONGITUDE, OWNER_CODE, OWNER_DESCR, STATE, COUNTY,FIPS_CODE, FIPS_NAME"}
    ]
  )
  yr = get_query_year(prompt)
  raw = response.choices[0].message.content
  
  suffix = ''
  if yr != 'NA':
    if ', ' in yr:
      start, stop = yr.split(', ')
      suffix = f' WHERE FIRE_YEAR BETWEEN {start} AND {stop}'
    else:
      try:
        yr = int(yr)
        suffix = f' WHERE FIRE_YEAR = {yr}'
      except:
        pass
      
  sql = 'SELECT ' + ', '.join(raw.split('\t')) + ' FROM `translate-413521.wildfire_aira.Fire`' + suffix
  return sql

def ret_v(context, prompt):
  response = client.chat.completions.create(
    model="ft:gpt-3.5-turbo-0125:nathannet:gpt-fuego-v1:9BoT37Uh",
    temperature = 0.15,
    max_tokens = 500,
    messages=[
      {"role": "system", "content": "You are a data science assistant. Please generate python code to answer the user's prompts."},
      {"role": "user", "content": f"Context: {context}, Prompt: {prompt} Create a result with only a single line of code using 'df' as an input."}
    ]
  )
  a = response.choices[0].message.content
  return a

def value_pipeline(code):
  try:
    try:
      out = eval(code.split('```python\n')[1].split('```')[0])
    except Exception as e:
      out = eval(code).replace('`','').replace('python','').replace('\n','')
  except Exception as e:
    out = eval(fix_secure(code, prompt).replace('`','').replace('python','').replace('\n',''))
  return out

def fix_secure(code, prompt):
  response = client.chat.completions.create(
  model="gpt-4-turbo",
  temperature = 0.1,
  max_tokens = 500,
  messages=[
    {"role": "system", "content": "You are a code fixing assistant. Respond only in correct python syntax without any text other than the python code itself given the prompt. If the code is already correct, return the exact input. Do no use print statements."},
    {"role": "user", "content": f'Code: {code}, Prompt:{prompt}'}
  ]
  )
  a = response.choices[0].message.content
  return a


def execute_code_in_pipeline(context):
  code = ret_v(context, prompt + ' Do not return a plot.')
  code_fixed = fix_secure(code, prompt).replace('python\n', '').replace('\n','')
  
  code_store.append(code)
  fixed_code_store.append(code_fixed)
  
  outs = {}
  for pipe in ['value_pipeline']:
    try:
      outs[pipe] = eval(f'''{pipe}(code_fixed)''')
    except Exception as e:
      outs[pipe] = f'info: {str(e)}'
  return outs

def multithread_code_output(context):
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(execute_code_in_pipeline, context) for _ in range(3)]
    results = [future.result() for future in concurrent.futures.as_completed(futures)]

    for t in executor._threads:
      add_script_run_ctx(t)
      
  return results

def package_output(prompt, results):
  response = client.chat.completions.create(
    model="gpt-4-turbo",
    temperature = 0,
    max_tokens = 1000,
    messages=[
      {"role": "system", "content": "You are a data analysis assistant. Please use the outputs to create a succinct, correct answer to the question using only the info you need."},
      {"role": "user", "content": f'Question: {prompt}, Outputs: {results}.'}
    ]
  )
  a = response.choices[0].message.content
  return a


#################################################################################
weather_api_key = "ca1906ce6ebf321aaaef2d1899a2b006"
weather_base_url = "http://api.openweathermap.org/data/2.5/weather?"

value_keys = {
    "B06011_001E": "Median Income",
    "B18120_002E": "Size of labor force",
    "B18120_012E": "Unemployed"
}

def get_economy(state_code, year=None):
  if year:
    c = Census("f507210223354169efae3b4780e18bf35714ec38", year=year) # need to re-init each time to avoid sync errors :(
  else:
    c = Census("f507210223354169efae3b4780e18bf35714ec38")

  r = c.acs1.get(('NAME', 'B06011_001E', 'B18120_002E', 'B18120_012E'), #combed through ACS tables for fields: https://www.census.gov/programs-surveys/acs/technical-documentation/table-shells.html
            {'for': f"state:{eval(f'states.{state_code}.fips')}"})[0]

  r = {k if k not in value_keys else value_keys[k]: v for k, v in r.items()}
  r['Unemployment rate'] = round(r['Unemployed'] / r['Size of labor force'], 4)
  if year:
    r['Year'] = year
  return r


def kelvin_to_fahrenheit(K):
    F = (K * (9/5)) - 459.67
    return round(F, 4)

def get_weather(place, weather_api_key):

  complete_url = weather_base_url + "appid=" + weather_api_key + "&q=" + place

  response = requests.get(complete_url)
  x = response.json()

  d = {k: kelvin_to_fahrenheit(v) if 200 < v < 400 else v for k, v in x['main'].items()}
  d['description_of_weather'] = x['weather'][0]['description']

  return d

def API_router(prompt):
  response = client.chat.completions.create(
    model="gpt-4-turbo",
    temperature = 0,
    max_tokens = 1000,
    messages=[
      {"role": "system", "content": "You are an API assistant which receives a prompt and determines if it involves either a weather API or a census API. The census API only returns information on 'median_income' and 'unemployment_rate' and the weather API only returns the following fields: 'temp' 'feels_like' 'temp_min' 'temp_max' 'pressure' 'humidity' 'description_of_weather'. Respond with either 'census','weather','both', or 'niether' given the prompt. Also include the year, state, and state code if applicable. Do not include any other text. Examples: Prompt: 'Which state has the most whales and how hot was it in 2019?' Response: 'weather 2019 NA NA', Prompt: 'How many ducks are in CA and what was their unemployment rate?' Response: 'census NA California CA'"},
      {"role": "user", "content": f'Prompt: {prompt}'}
    ]
  )

  return response.choices[0].message.content

def get_api(prompt):
  try:
    routed = API_router(prompt)
    st.sidebar.info('API determination info:\n' + str(routed), icon="ℹ️")
    print(routed)
    api, year, state, state_code = routed.split(' ')

    if api == 'niether':
      return None
    if year == 'NA':
      year = None
    else:
      year = int(year)

    if api == 'niether':
      return None
    elif api == 'census':
      r = get_economy(state_code, year)
    elif api == 'weather':
      r = get_weather(state, weather_api_key)
    elif api == 'both':
      r = {**get_economy(state_code, year), **get_weather(state, weather_api_key)}
    try:
      return r
    except:
      return None
  except ValueError:
    return None
##############################################################################################

client = openai.OpenAI(api_key = OpenAIKey)


st.set_page_config(page_title="gpt-fuego: AI for conversational data analysis", page_icon="🔥")
st.title("🔥 gpt-:orange[fuego]")
st.markdown("An AI Agent for Conversational Database Analysis (Wildfire Demo)")

if "messages" not in st.session_state:
  st.session_state.messages = []

for message in st.session_state.messages:
  if message["role"] == 'gpt-fuego':
    with st.chat_message(message["role"], avatar="🔥"):
        st.markdown(message["content"])
  else:
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

prompt = st.chat_input("Say something")
  
if prompt:
  st.chat_message('user').write(prompt)
  st.session_state.messages.append({"role": "user", "content": prompt})

  my_bar = st.progress(0, text='generating sql query')
  query = gen_sql(prompt)
  st.sidebar.info('SQL req. to BQ:\n' + str(query), icon="ℹ️")

  my_bar.empty()
  my_bar = st.progress(10, text='scrubbing prompt')
  pre_scrub = prompt
  prompt = scrub_prompt(prompt)
  print(prompt)
  
  my_bar.empty()
  my_bar = st.progress(20, text='gathering data from BigQuery')
  query_job = client_bq.query(query)

  my_bar.empty()
  my_bar = st.progress(30, text='generating dataframe')
  df = query_job.to_dataframe()

  wildfire_context = f'''```python\n# Connect to the sqlite db file and retrieve     data as Pandas data frame.
  cnx = sqlite3.connect('archive/FPA_FOD_20170508.sqlite')
  sql = "select * from fires"
  df = pd.read_sql_query(sql, cnx)\n# Cols = {' '.join(df.columns)}```'''
  print(wildfire_context)
  my_bar.empty()
  my_bar = st.progress(70, text='generating and executing analysis code versions')
  code_store = []
  fixed_code_store = []
  results = multithread_code_output(wildfire_context)
  st.sidebar.info('Multithreaded initial code:\n' + str(code_store), icon="ℹ️")
  st.sidebar.info('Fixed code:\n' + str(fixed_code_store), icon="ℹ️")
  st.sidebar.info('Code execution:\n' + str(results), icon="ℹ️")
  
  my_bar.empty()
  my_bar = st.progress(85, text='interpreting results')
  o = package_output(pre_scrub, results)
  
  my_bar.empty()
  my_bar = st.progress(90, text='routing')
  post_api = (get_api(f'{str(pre_scrub)} | {str(results)}'))
  st.sidebar.info('API info:\n' + str(post_api), icon="ℹ️")

  my_bar.empty()
  my_bar = st.progress(95, text='Runnning external API(s)')
  if post_api:
    o = package_output(pre_scrub, str(results)+ ' | ' +str(post_api))

  my_bar.empty()
  st.chat_message('gpt-fuego', avatar="🔥").write(o)
  
  st.session_state.messages.append({"role": "gpt-fuego", "avatar":"🔥", "content": o})