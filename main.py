from sqlalchemy.engine import URL
from sqlalchemy import create_engine, event, text
from azure.identity import DefaultAzureCredential
import pyodbc
import struct
import os
from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentType, create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
import azure.cognitiveservices.speech as speechsdk

# Azure SQL details
sql_server = ""
database = "BatchStorage"
driver = "ODBC+Driver+18+for+SQL+Server"
AZURE_SPEECH_KEY = ""
AZURE_SPEECH_REGION = "uksouth"


speech_config = speechsdk.SpeechConfig(
    subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION)
speech_config.speech_recognition_language = "en-US"

audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
speech_recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config, audio_config=audio_config)

print("You can speak now. I'm listening...")
speech_recognition_result = speech_recognizer.recognize_once_async().get()
output = speech_recognition_result.text

connection_string = f"mssql+pyodbc://{
    sql_server}.datawarehouse.fabric.microsoft.com/{database}?driver={driver}"


llm = AzureChatOpenAI(
    openai_api_type="azure",
    openai_api_key=os.getenv("openaiaccesskey"),
    azure_endpoint="https://mango-bush-0a9e12903.5.azurestaticapps.net/api/v1",
    model="gpt-4-turbo-2024-04-09",
    openai_api_version="2024-06-01")

engine = create_engine(connection_string)


@event.listens_for(engine, 'do_connect')
def do_connect(dialect, conn_rec, cargs, cparams):
    azure_credentials = DefaultAzureCredential()
    result = azure_credentials.get_token(
        "https://database.windows.net/.default")
    raw_token = result.token.encode("utf-16-le")
    token_struct = struct.pack(
        f'=I{len(raw_token)}s', len(raw_token), raw_token)
    cargs[0] = cargs[0].replace(";Trusted_Connection=Yes", "")
    attrs_before = cparams.setdefault('attrs_before', {})
    attrs_before[1256] = bytes(token_struct)
    return dialect.connect(*cargs, **cparams)


with engine.connect() as connection:
    result = connection.execute(text(
        "SELECT * FROM curatedemployeetable"))
    for row in result:
        print(row)


print('database connected succesfully')

user_db = SQLDatabase(engine, include_tables=["curatedemployeetable"])

sql_toolkit = SQLDatabaseToolkit(db=user_db, llm=llm)

sqldb_agent = create_sql_agent(
    llm=llm,
    db=user_db,
    agent_type='openai-tools',
    verbose=True
)


# Give me the list of employees who live in London and whose Domain is Fabric

print("Your question is.......")
print(output)
sqldb_agent.run(output)
