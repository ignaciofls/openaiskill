import logging
import azure.functions as func
import json, requests, time, os, logging, re
import openai
from time import sleep
#from http.client import HTTPConnection

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        body = json.dumps(req.get_json())
    except ValueError:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )
    
    if body:
        result = compose_response(body)
        return func.HttpResponse(result, mimetype="application/json")
    else:
        return func.HttpResponse(
             "Invalid body",
             status_code=400
        )

def compose_response(json_data):
    values = json.loads(json_data)['values']

    # Prepare the Output before the loop
    results = {}
    results["values"] = []

    for value in values:
        outputRecord = transform_value(value)
        if outputRecord != None:
            results["values"].append(outputRecord)
    return json.dumps(results, ensure_ascii=False)

def transform_value(value):
    try:
        recordId = value['recordId']
    except AssertionError  as error:
        return None

    # Validate the inputs
    try:         
        assert ('data' in value), "'data' field is required."
        data = value['data']        
        assert ('text' in data), "'text' corpus field is required in 'data' object."
    except AssertionError  as error:
        return (
            {
            "recordId": recordId,
            "data":{},
            "errors": [ { "message": "Error:" + error.args[0] }   ]
            })

    try:
        result = get_aoai_result (value)
    except:
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Could not complete operation for record." }   ]
            })

    return ({
            "recordId": recordId,
            "data": {
                "text": result
                    }
            })

# Function to submit the analysis job towards the Text Analytics (TA) API
def get_aoai_result (value):
    ## Debug logging, useful if you struggle with the body sent to the endpoint. Uncomment from http.client too 
    #log = logging.getLogger('urllib3')
    #log.setLevel(logging.DEBUG)    
    # logging from urllib3 to console
    #ch = logging.StreamHandler()
    #ch.setLevel(logging.DEBUG)
    #log.addHandler(ch)
    ##print statements from `http.client.HTTPConnection` to console/stdout
    #HTTPConnection.debuglevel = 1 
    
    openai.api_key = os.environ["openai.api_key"]
    openai.api_base = os.environ["openai.api_base"]
    openai.api_version = os.environ["openai.api_version"]
    openai.api_type = os.environ["openai.api_type"]

    #Based on your use case you can change the prompt to let GPT-3 understand your intent, similarly with the engine to find the best suited model
    prompt = 'Summarize the following document:                    SUMMARY ---'
    engine = 'text-davinci-002'
    corpus = str(value['data']['text'])


    temp=0.5
    max_tokens = 150
    top_p=1.0
    freq_pen=0.25
    pres_pen=0.0
    stop=['<<END>>']
    max_retry = 3
    retry = 0

    #if corpus length is longer than 11000 characters we trim it, future improvement would be to split it into multiple requests
    if len(corpus) > 11000:
        corpus1 = corpus[:11000]
    else:
        corpus1 = corpus
    prompt = prompt.replace('SUMMARY', corpus1).encode(encoding='ASCII',errors='ignore').decode()
    while True:
        try:
            sleep(1) # to avoid hitting a potential rate limit
            response = openai.Completion.create(
                engine=engine,
                prompt=prompt,
                temperature=temp,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                stop=stop)
            text = response['choices'][0]['text'].strip()
            text = re.sub('\s+', ' ', text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(1)