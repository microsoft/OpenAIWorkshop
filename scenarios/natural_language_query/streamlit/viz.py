#ro run the solution: streamlit run viz.py
import streamlit as st
import random
import pandas as pd
from query_viz import AnalyzeGPT
st.title('Data Analysis Assistant')
question = st.text_area("Ask me a  question in sales")
if st.button("Submit"):  
    # Call the execute_query function with the user's question  
    analyzer = AnalyzeGPT()
    analyzer.run(question, st)



