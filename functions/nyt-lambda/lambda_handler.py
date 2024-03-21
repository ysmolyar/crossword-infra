from bs4 import BeautifulSoup
from datetime import datetime
import json
import requests
import boto3

ORACLE_URI = "https://www.nytimes.com/svc/crosswords/v2/oracle/daily.json"
PUZZLE_DETAILS_URI = "https://www.nytimes.com/svc/crosswords/v2/puzzle/{}.json"
NYT_LOGIN_URI = "https://myaccount.nytimes.com/svc/ios/v2/login"
DATE = "3/21/2024"
XWORD_INFO_URI = "https://www.xwordinfo.com/Crossword?date={}"
DIMENSION = 15
SUNDAY_DIMENSION = 21

DYNAMO_TABLE_NAME = "CrosswordInfraStack-CrosswordTableC285ED21-111C8OOVQD3G"

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def create_map_from_divs(divs, direction):
    solution_map = {}
    index = 0
    while index < len(divs):
        val = divs[index].text
        if(val.isnumeric()):
            next_div = divs[index+1].text
            if next_div:
                next_div = next_div.split(':')
                clue, answer = next_div[0].strip(), next_div[1].strip()
                # list comprehension that filters out bad characters
                clue_path = [s for s in clue if s.isalnum() or s.isspace()]

                # rejoin intermediate list into a string
                clue_path = "".join(clue_path).replace(' ', '-').replace('--', '-').lower()
                clue_path = clue_path[1:] if clue_path[0] == '-' else clue_path
                solution_map[clue] = { 
                    "number": val, 
                    "direction": direction, 
                    "answer": answer,
                    "clue_path": clue_path,
                    "publish_date": DATE
                    }
                index+=1
        index+=1 
    return solution_map

def handler(event, context):
    # 1. GET xword_info webpage

    # get current date
    current_date = datetime.now().strftime("%-m/%-d/%Y")

    # Send a GET request to the URL
    response = requests.get(XWORD_INFO_URI.format(DATE))
    print(response)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the container of all 'across' clues and answers
        across_container = soup.find(id="ACluesPan")

        # Find all divs in the container
        divs = across_container.find_all("div")
        solution_map = {}


        # iterate over all divs. They follow the patterns
        #
        # <div>34</div>
        # <div>Buyer : <a href="/Finder?w=VENDEE">VENDEE</a></div>
        # <div>35</div>
        # <div>Sudden arrival : <a href="/Finder?w=INRUSH">INRUSH</a></div>
        # <div>37</div>
        # 
        # Turn this structure into a dictionary
        # {
        #    "Buyer": {
        #      "number": "34",
        #      "direction": "across",
        #      "answer": "VENDEE",
        #      "clue_path": "buyer"
        #    },
        #    "Sudden arrival": {
        #      "number": "35",
        #      "direction": "across",
        #      "answer": "INRUSH",
        #      "clue_path": "sudden-arrival"
        #    },
        # }
        solution_map = solution_map | create_map_from_divs(divs, "across")

        # Find the container of all 'down' clues and answers
        down_container = soup.find(id="DCluesPan")

        # Find all divs in the container
        divs = down_container.find_all("div")

        solution_map = solution_map | create_map_from_divs(divs, "down")

        print(solution_map)

        print(f"{len(solution_map.keys())} pairs found from xwordinfo.com for date {DATE}")
        
        s3 = boto3.client('s3')
        
        # Initialize DynamoDB client
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
#         # Define the DynamoDB table name
#         root_html_links = ''''''
#         clues_html = '''
# <div><a href="/{}/index.html" class="crossword-link">{}{} {}: View Answer</a></div>
# '''
        # Iterate over the dictionary
        for clue, clue_data in solution_map.items():
            number = clue_data.get('number', '')
            direction = clue_data.get('direction', '')
            clue_path = clue_data.get('clue_path', '')
            answer = clue_data.get('answer', '')
            publish_date = clue_data.get('publish_date', '')


            # Load HTML template
            # with open('template/answer-page.html', 'r') as file:
            #     template_content = file.read()
            
            # # Replace placeholders with actual values
            # rendered_html = template_content.replace('{{CLUE}}', clue)
            # rendered_html = rendered_html.replace('{{ANSWER}}', answer)
            
            # # TODO: better dry run functionality
            # try:
            #     with open(f"dry-run/{clue_path}-index.html", "x") as file:
            #         file.write(rendered_html)
            # except Exception as e:
            #     print(e.strerror)
            
            
            # # save html to list for root object update
            # root_html_links += (clues_html.format(clue_path, number, direction[0], clue))

            # # Upload rendered HTML to S3 bucket
            # # TODO: better way of passing this bucket name. maybe env var from cdk stack
            # print(f"Putting s3 object with key {clue_data['clue_path']}/index.html")
            # s3.put_object(
            #     Bucket='crosswordinfrastack-websitebucket75c24d94-geqg8lfkgxrr',
            #     Key=f"{clue_data['clue_path']}/index.html",
            #     Body=rendered_html.encode('utf-8'),
            #     ContentType='text/html'
            # )
            
            # Create item to put into DynamoDB
            item = {
                'number': {'S': number},
                'direction': {'S': direction},
                'answer': {'S': answer},
                'clue_path': {'S': clue_path},
                'publish_date': {'S': publish_date},
                'clue': {'S': clue}
            }
            
            try:
                # Put item into DynamoDB table
                response = dynamodb.put_item(
                    TableName=DYNAMO_TABLE_NAME,
                    Item=item
                )
                print("Item added successfully:", response)
            except Exception as e:
                print("Error adding item to DynamoDB:", e)

        # write a list of new additions to root object
        # TODO: right now we have a copy of the html file as a template, we will need to read the
        # file from S3 and then inject more intelligently. probably by div or class
        # Load root object HTML template
        # with open('template/root-object.html', 'r') as file:
        #     root_content = file.read()

        # # Replace placeholders with actual values
        # rendered_html = root_content.replace('{{CLUES}}', root_html_links) 
        # rendered_html = rendered_html.replace('{{DATE}}', DATE) 

        # with open(f"dry-run/index.html", "w") as file:
        #     file.write(rendered_html)
    
        # # update root object
        # print("Updating root object at index.html")
        # s3.put_object(
        #     Bucket='crosswordinfrastack-websitebucket75c24d94-geqg8lfkgxrr',
        #     Key=f"index.html",
        #     Body=rendered_html.encode('utf-8'),
        #     ContentType='text/html'
        # )
        return {
            'statusCode': 200,
            'body': json.dumps(f"${DATE} crossword parsed and uploaded to DynamoDB successfully!")
        }

handler("", "")