import os
import boto3
import logging
from datetime import datetime, timezone
from langchain.prompts import PromptTemplate
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
from langchain.chains import LLMChain
from dotenv import load_dotenv
import sys
import time

load_dotenv(override=True)

LOG_GROUP_NAME = os.getenv("LOG_GROUP_NAME")
REGION_NAME = os.getenv("REGION_NAME")




def get_log_events(log_group: str, limit: int = 50, minutes_ago: int = 5):
    """Fetches recent VPC Flow Logs from AWS CloudWatch."""
    try:
        start_time = int((time.time() - (minutes_ago * 60)) * 1000)  # Convert to milliseconds
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            limit=limit,
            startTime=start_time
        )
        return response.get("events", [])
    except Exception as e:
        logging.error(f"Error fetching logs: {e}")
        return []

def convert_timestamp_to_human_readable(events):
    """Converts timestamps in milliseconds to a human-readable UTC format."""
    return [
        {
             **event,
            "timestamp": datetime.fromtimestamp(event["timestamp"] / 1000, timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for event in events
    ]


load_dotenv()

# Initialize AWS Logs Client using the region from config
logs_client = boto3.client("logs", region_name=REGION_NAME)

#retrieve logs from CloudWatch logs
events = get_log_events(LOG_GROUP_NAME)
print(events)
if not events:
    logging.warning("No logs retrieved!")
    sys.exit("No logs retrieved. Exiting the program.")

# Convert timestamps in logs
converted_events = convert_timestamp_to_human_readable(events)


user_queries = [
        "Please show the connections with Protocol equals 6 and Destination Port equals 22. Do not return any other connections.",
        "What are the connections from Source IP 67.71.82.155?",
        "Show me all the connections",
        "What is the last source IP address that connected last to my server with address 10.1.9.108?" ,
        "Looking at all the flows, can you please list the destination ports where the destination equals 10.1.9.108 that have the action ACCEPT? Only list the destination ports, not the full details."
        "Can you figure out if there are any clear text (unencrypted protocols) such as HTTP or Telnet being used?"
    ]



prompt_template = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant analyzing VPC Flow Logs. The user will ask questions on the logs, and you need to answer accordingly.
    Answer only with the extracted information in this format if there is a matching connection or connections:
    timestamp: <timestamp>
    Source IP: <srcaddr>
    Destination IP: <dstaddr>
    Source Port: <srcport>
    Destination Port: <dstport>
    Protocol: <protocol>
    Action: <action>

    If no matching connections are found, respond with: "There are no matching connections."

    All timestamps are in UTC.

    VPC Flow Logs:
    {logs}"""),  # Removed the extra closing parenthesis here

    ("human", "{user_query}")  # Corrected formatting
])

model = ChatOpenAI(model="gpt-4o")
# Create the combined chain using LangChain Expression Language (LCEL)
chain = prompt_template | model | StrOutputParser()

for user_query in user_queries:
    result = chain.invoke({"logs": converted_events, "user_query": user_query})
    print(f"Answer for the question: {user_query}\n")
    print(result)
    print("\n" + "-"*80 + "\n")
