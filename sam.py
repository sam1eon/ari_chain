import streamlit as st
from transformers import logging
from langchain.llms import TextGen
from langchain.prompts import PromptTemplate
from langchain import LLMChain
import streamlit as st
import streamlit as st
from pyvis.network import Network
from CustomLibrary.Custom_Agent import CustomLLMChain, CustomLLMChainAdditionalEntities
from CustomLibrary.Custom_Prompts import (
    Entity_type_Template_add,
    Entity_type_Template_Alpaca, 
    Entity_Extraction_Template_alpaca, 
    Entity_type_Template_airo, 
    Entity_Extraction_Template_airo, 
    Entity_Extraction_Template,  
    Entity_type_Template, 
    Additional_Entity_Extraction_Template,
    Final_Answer_Template,
    Additional_Entity_Extraction_Template_Vicuna,
    Entity_type_Template_add_Vicuna,
    Entity_type_Template_add_Alpaca,
    Entity_Extraction_Template_alpaca,
    Additional_Entity_Extraction_Template_Alpaca,
    Entity_type_Template_add_Upstage,
    Entity_Extraction_Template_Upstage,
    Additional_Entity_Extraction_Template_Upstage,
    Entity_type_Template_Upstage,
    Graph_Answer_Gen_Template_Upstage

)
from CustomLibrary.App_Utils import(
    get_umls_info, 
    extract_entities, 
    get_names_list, 
    get_names_list, 
    get_entity_types, 
    get_additional_entity_umls_dict,
    create_and_display_network
)
from CustomLibrary.Graph_Visualize import parse_relationships_pyvis
from CustomLibrary.samGraphClass import samGraphClass
# what is the relationship between alzheimer's and diabetes, and could sildenafil be used to treat both?
#Could there be a synergistic drug-drug interaction between lamotrigine and rivastigmine for lewy body dementia?
# Set logging verbosity
logging.set_verbosity(logging.CRITICAL)
@st.cache_data()
def initialize_models():
    model_url = "https://laid-laboratories-picnic-internationally.trycloudflare.com/"
    local_model_url = "http://127.0.0.1:5000/"
    llm = TextGen(model_url=model_url, max_new_tokens=2048)
    local_llm = TextGen(model_url=local_model_url, max_new_tokens=2048)
    #Entity_extraction_prompt = PromptTemplate(template=Entity_Extraction_Template_Upstage, input_variables=["input"])
    Entity_extraction_prompt = PromptTemplate(template=Entity_Extraction_Template, input_variables=["input"])
    #entity_extraction_chain = CustomLLMChain(prompt=Entity_extraction_prompt, llm=llm, output_key="output",)
    entity_extraction_chain = CustomLLMChain(prompt=Entity_extraction_prompt, llm=llm, output_key="output",)
    return llm, entity_extraction_chain, local_llm

@st.cache_data()
def initialize_knowledge_graph():
    uri = "neo4j://localhost:7687"
    username = "neo4j"
    password = "NeO4J"
    return uri, username, password

st.set_page_config(layout="wide")
st.title("Multi-Hop Question Answering")

# Define the progress bar
progress_bar = st.empty()

# Define the callback function to update the progress bar
def progress_callback(progress):
    progress_bar.progress(progress)

###########################################################################################################################################################################################################################################

#additional_entity_extraction_prompt = PromptTemplate(template=Additional_Entity_Extraction_Template_Upstage, input_variables=["input", "entities"])
additional_entity_extraction_prompt = PromptTemplate(template=Additional_Entity_Extraction_Template, input_variables=["input", "entities"])
llm, entity_extraction_chain, local_llm = initialize_models()
#llm, local_llm, entity_extraction_chain = initialize_models()
uri, username, password = initialize_knowledge_graph()
additional_entity_extraction_chain = CustomLLMChainAdditionalEntities(prompt=additional_entity_extraction_prompt, llm=llm, output_key="output",)

#Entity_type_prompt = PromptTemplate(template=Entity_type_Template_Upstage, input_variables=["input"])
Entity_type_prompt = PromptTemplate(template=Entity_type_Template, input_variables=["input"])
#Entity_type_prompt_add = PromptTemplate(template=Entity_type_Template_add_Upstage, input_variables=["input"])
Entity_type_prompt_add = PromptTemplate(template=Entity_type_Template_add, input_variables=["input"])
Entity_type_chain = LLMChain(prompt=Entity_type_prompt, llm=llm)
#Entity_type_chain = LLMChain(prompt=Entity_type_prompt, llm=local_llm)
Entity_type_chain_add = LLMChain(prompt=Entity_type_prompt_add, llm=llm)
#Entity_type_chain_add = LLMChain(prompt=Entity_type_prompt_add, llm=local_llm)

question = st.chat_input("Enter your question")
if question:
    with st.chat_message("user"):
        st.write(question)
    with st.spinner("Checking drug interaction..."):
        # Entity extraction
        entities, additional_entities = extract_entities(question, entity_extraction_chain, additional_entity_extraction_chain)

        entities_umls_ids = get_umls_info(entities)

        names_list = get_names_list(entities_umls_ids)

        entity_types = get_entity_types(Entity_type_chain, names_list)

###########################################################################################################################################################################################################################################

        if additional_entities:
            additional_entity_umls_dict = get_additional_entity_umls_dict(additional_entities, Entity_type_chain_add)
            print(additional_entity_umls_dict)

            keys_to_remove = []
            for key, value in additional_entity_umls_dict.items():
                # Check if any value is empty
                if any(v is None or v == '' for v in value.values()):
                    # Add the key to the list of keys to remove
                    keys_to_remove.append(key)

            # Remove the keys outside the loop
            for key in keys_to_remove:
                del additional_entity_umls_dict[key]

            knowledge_graph = samGraphClass(uri, username, password, local_llm, entity_types, additional_entity_types=additional_entity_umls_dict)
        else:
            knowledge_graph = samGraphClass(uri, username, password, local_llm, entity_types)

        # Query the knowledge graph
        graph_query = knowledge_graph._call(names_list, 
                                            question, 
                                            generate_an_answer=True, 
                                            progress_callback=progress_callback)
        
        context = graph_query["result"]
        all_rels = graph_query['all_rels']

        #rint(all_rels)
        print(len(all_rels))
        nodes = set()

        nodes, edges = parse_relationships_pyvis(all_rels)

        ckg_container = st.container()
        with ckg_container:
            with st.chat_message("assistant"):
                st.write("CKG Network:")
            with st.chat_message("assistant"):
                create_and_display_network(nodes, edges, '#fff6fe', "CKG", names_list[0], names_list[1])
            with st.chat_message("assistant"):
                st.write("CKG_Answer:")
            with st.chat_message("assistant"):
                st.write(context)
        
