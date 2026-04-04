import sys
import json
import csv
import os
import re
import time
from google import genai
from dotenv import load_dotenv
 
load_dotenv()


# Read the CSV file into a DataFrame
df = pd.read_csv("input.csv")
print(df.head())

#