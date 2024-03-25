from bs4 import BeautifulSoup
from datetime import datetime
import json
import requests
import boto3

# how to set a manual datetime
#datetime(year=2024, month=3, day=24)
XWORD_INFO_URI = "https://www.xwordinfo.com/Crossword?date={}"
DIMENSION = 15
SUNDAY_DIMENSION = 21

DYNAMO_TABLE_NAME = "CrosswordInfraStack-CrosswordTableC285ED21-111C8OOVQD3G"
ASSET_BUCKET_NAME = "crosswordinfrastack-websitebucket75c24d94-fj4j7w0e6nfq"
CLUE_TEMPLATE_S3_PATH = "clue-path/clue.html"
CLUE_TEMPLATE_LOCAL_PATH = "/tmp/clue.html"
PUZZLE_TEMPLATE_S3_PATH = "puzzle-path/puzzle.html"
PUZZLE_TEMPLATE_LOCAL_PATH = "/tmp/puzzle.html"
HOME_PAGE_S3_PATH = "index.html"
HOME_PAGE_LOCAL_PATH = "/tmp/index.html"
# takes datetime and makes string like 3/21/24
def format_date_for_xword(date):
    return date.strftime("%-m/%-d/%Y")

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def create_list_from_divs(divs, direction, date):
        # iterate over all divs. They follow the patterns
        #
        # <div>34</div>
        # <div>Buyer : <a href="/Finder?w=VENDEE">VENDEE</a></div>
        # <div>35</div>
        # <div>Sudden arrival : <a href="/Finder?w=INRUSH">INRUSH</a></div>
        # <div>37</div>
        # 
        # Turn this structure into a dictionary
        # [
        #    {
        #      "clue": "Buyer"
        #      "number": "34",
        #      "direction": "across",
        #      "answer": ["VENDEE"],
        #      "clue_path": "buyer",
        #      "published_date": "3/21/24",
        #      "dotw": 6
        #    },
        #    {
        #      "clue": "Sudden arrival"
        #      "number": "35",
        #      "direction": "across",
        #      "answer": ["INRUSH"],
        #      "clue_path": "sudden-arrival",
        #      "published_date": "3/21/24",
        #      "dotw": 6
        #    },
        # ]

    solutions = []
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
                clue_path = clue_path[:-1] if clue_path.endswith('-') else clue_path

                solutions.append({ 
                    "clue": clue,
                    "number": val, 
                    "direction": direction, 
                    "answer": answer,
                    "clue_path": clue_path,
                    "publish_date": format_date_for_xword(date),
                    "dotw": date.weekday()
                    })
                index+=1
        index+=1 
    return solutions

# returns clue object from dynamo
# need this to get the list of answers rather than just todays answer. for templating
def add_clue_to_dynamo(dynamodb, clue_data):
    number = clue_data.get('number', '')
    direction = clue_data.get('direction', '')
    clue_path = clue_data.get('clue_path', '')
    new_answer = clue_data.get('answer', '')
    answer = [new_answer]
    publish_date = clue_data.get('publish_date', '')
    clue = clue_data.get('clue', '')
    
    try:
        # first look in Dynamo to see if the clue already exists. If yes, add the answer
        response = dynamodb.get_item(
            TableName=DYNAMO_TABLE_NAME,
            Key={
                'clue_path': {'S': clue_path}
            }    
        )

        # Check if the item exists in the response
        if 'Item' in response:
            item = response['Item']
            print("Clue already exists in dynamo:", item['clue_path']['S'])
            existing_answers = json.loads(item['answer']['S'])
            print("existing answers:", existing_answers)
            # if new answer already in list of existing answers, don't add it again
            if new_answer not in existing_answers:
                print(f"new answer {new_answer} is not in existing answers. adding it")
                answer = existing_answers.append(new_answer)
            else:
                print(f"new answer {new_answer} is already in existing answers. updating item in dynamo but leaving answer key alone")
        else:
            print(f"Clue {clue_path} does not already exist in dynamo")
    except Exception as e:
        print("Error reading clues from DynamoDB:", e)   

    try:
        # Create item to put into DynamoDB
        item = {
            'number': {'S': number},
            'direction': {'S': direction},
            'answer': {'S': json.dumps(answer)},
            'clue_path': {'S': clue_path},
            'publish_date': {'S': publish_date},
            'clue': {'S': clue}
        }
        # Put item into DynamoDB table
        response = dynamodb.put_item(
            TableName=DYNAMO_TABLE_NAME,
            Item=item
        )
        print(f"Added {clue_path} successfully:", response)
    except Exception as e:
        print("Error adding item to DynamoDB:", e)   

    return {
        'number': number,
        'direction': direction,
        'answer': answer,
        'clue_path': clue_path,
        'publish_date': publish_date,
        'clue': clue
    }

def create_clue_page_html_from_template(s3, clue_data):
    date_string = clue_data.get('publish_date', '')
    parsed_date = datetime.strptime(date_string, "%m/%d/%Y")
    dotw_string = parsed_date.strftime("%A")
    month_string = parsed_date.strftime("%B")
    day_string = parsed_date.strftime("%d")
    year_string = parsed_date.strftime("%Y")
    url_date = parsed_date.strftime("%m-%d-%y")

    # Load HTML template
    print("reading template from local file and injecting values")
    with open(CLUE_TEMPLATE_LOCAL_PATH, 'r') as file:
        template_content = file.read()
        template_content = template_content.replace('{{CLUE}}', clue_data.get('clue', ''))
        template_content = template_content.replace('{{URL_DATE}}', url_date)
        template_content = template_content.replace('{{DOTW}}', dotw_string)
        template_content = template_content.replace('{{MONTH}}', month_string)
        template_content = template_content.replace('{{MONTH_FIRST3}}', month_string[:3])
        template_content = template_content.replace('{{MONTH_REST}}', month_string[3:])
        template_content = template_content.replace('{{DAY}}', day_string)
        template_content = template_content.replace('{{YEAR}}', year_string)

        soup = BeautifulSoup(template_content, 'html.parser')

        # Find the <div> element with class "answer"
        answer_div = soup.find('div', class_='answer')
        # Create a new <strong> element
        for ans in clue_data.get('answer'):
            print(f"adding answer {ans}")
            new_div = soup.new_tag('div')
            new_answer = soup.new_tag('strong')
            new_answer.string = ans  
            # Append the new <strong> element to the answer <div>
            new_div.append(new_answer)
            answer_div.append(new_div)

        print(f"Putting s3 object with key {clue_data['clue_path']}-crossword-clue/index.html")
        s3.put_object(
            Bucket=ASSET_BUCKET_NAME,
            Key=f"{clue_data['clue_path']}-crossword-clue/index.html",
            Body=soup.prettify().encode('utf-8'),
            ContentType='text/html'
        )

def create_puzzle_page_html_from_template(s3, answers_data):
    clue_data = answers_data[0]
    date_string = clue_data.get('publish_date', '')
    parsed_date = datetime.strptime(date_string, "%m/%d/%Y")
    dotw_string = parsed_date.strftime("%A")
    month_string = parsed_date.strftime("%B")
    day_string = parsed_date.strftime("%d")
    year_string = parsed_date.strftime("%Y")
    url_date = parsed_date.strftime("%m-%d-%y")

    # Filter clue_data based on direction
    across_clues = [clue for clue in answers_data if clue["direction"] == "across"]
    print(f"iterating over {len(across_clues)} across clues")
    down_clues = [clue for clue in answers_data if clue["direction"] == "down"]
    print(f"iterating over {len(down_clues)} down clues")

    # Sort the filtered lists based on number
    across_clues.sort(key=lambda x: int(x["number"]))
    down_clues.sort(key=lambda x: int(x["number"]))

    # Load HTML template
    print("reading template from local file and injecting values")
    with open(PUZZLE_TEMPLATE_LOCAL_PATH, 'r') as file:
        template_content = file.read()
        template_content = template_content.replace('{{CLUE}}', clue_data.get('clue', ''))
        template_content = template_content.replace('{{URL_DATE}}', url_date)
        template_content = template_content.replace('{{DOTW}}', dotw_string)
        template_content = template_content.replace('{{MONTH}}', month_string)
        template_content = template_content.replace('{{MONTH_FIRST3}}', month_string[:3])
        template_content = template_content.replace('{{MONTH_REST}}', month_string[3:])
        template_content = template_content.replace('{{DAY}}', day_string)
        template_content = template_content.replace('{{YEAR}}', year_string)

        soup = BeautifulSoup(template_content, 'html.parser')


        # Find the <div> element with class
        across_table = soup.find('table', class_='ACrossTable')
        down_table = soup.find('table', class_='DCrossTable')

        for clue in across_clues + down_clues:
            '''
            <tr>
                <td class="left-column">Data 1</td>
                <td class="right-column">Data 2</td>
            </tr>
            '''
            print(f"adding clue {clue['number']}{clue['direction']}: {clue['answer']}")
            new_row = soup.new_tag('tr')
            clue_td = soup.new_tag('td')
            clue_td.attrs['class'] = 'left-column'
            clue_td.string = f"{clue['number']} {clue['clue']}"
            ans_td = soup.new_tag('td')
            ans_td.attrs['class'] = 'right-column'
            
            ans_a = soup.new_tag('a')
            ans_a.attrs['href'] = f"/{clue['clue_path']}-crossword-clue/"
            ans_a.string = clue['answer']
            ans_td.append(ans_a)

            new_row.append(clue_td)
            new_row.append(ans_td)
            # append to appropriate container
            if clue['direction'] == 'across':
                across_table.append(new_row) 
            if clue['direction'] == 'down':
                down_table.append(new_row)

        print(f"Putting s3 object with key nyt-crossword-answers-{url_date}/index.html")
        s3.put_object(
            Bucket=ASSET_BUCKET_NAME,
            Key=f"nyt-crossword-answers-{url_date}/index.html",
            Body=soup.prettify().encode('utf-8'),
            ContentType='text/html'
        )

def update_home_page_html_from_template(s3, answers_data):
    clue_data = answers_data[0]
    date_string = clue_data.get('publish_date', '')
    parsed_date = datetime.strptime(date_string, "%m/%d/%Y")
    dotw_string = parsed_date.strftime("%A")
    month_string = parsed_date.strftime("%B")
    day_string = parsed_date.strftime("%d")
    year_string = parsed_date.strftime("%Y")
    url_date = parsed_date.strftime("%m-%d-%y")

    # Load HTML template
    print("reading template from local file and injecting values")
    with open(HOME_PAGE_LOCAL_PATH, 'r') as file:
        template_content = file.read()

        soup = BeautifulSoup(template_content, 'html.parser')
        # Find the <div> element with class articles
        articles_container = soup.find('div', class_='articles')
        # Count the number of articles within the container
        articles = articles_container.find_all('article')
        print("Number of articles on the home page:", len(articles))
        # delete last elemenet if we have a week or more already
        if len(articles) >= 8:
            last_article = articles[-1]
            last_article.extract()

        # Create the article element with specified class
        article = soup.new_tag("article", **{"class": "box post post-excerpt"})

        # Create the header element
        header = soup.new_tag("header")

        # Create the h2 element
        h2 = soup.new_tag("h2")
        a = soup.new_tag("a", href=f"/nyt-crossword-answers-{url_date}/")
        a.string = f"NYT Crossword Answers - {dotw_string} {month_string} {day_string}, {year_string}"
        h2.append(a)

        # Create the p element for author info
        p_author = soup.new_tag("p")
        p_author.string = "NYT Crossword Answers/ By Yoni Smolyar"

        # Append h2 and p_author to header
        header.append(h2)
        header.append(p_author)

        # Create the div.info element
        div_info = soup.new_tag("div", **{"class": "info"})

        # Create the span.date element
        span_date = soup.new_tag("span", **{"class": "date"})
        span_month = soup.new_tag("span", **{"class": "month"})
        span_month.string = month_string[:3]
        span_month_inner = soup.new_tag("span")
        span_month_inner.string = month_string[3:]  # Append last chars to the month
        span_day = soup.new_tag("span", **{"class": "day"})
        span_day.string = day_string
        span_year = soup.new_tag("span", **{"class": "year"})
        span_year.string = f", {year_string}"
        span_month.append(span_month_inner)
        span_date.append(span_month)
        span_date.append(span_day)
        span_date.append(span_year)

        # Create the ul.stats element
        ul_stats = soup.new_tag("ul", **{"class": "stats"})

        # Create list items for statistics
        for icon_class, count in [("fa-comment", "16"), ("fa-heart", "32"), ("fa-twitter", "64"), ("fa-facebook-f", "128")]:
            li = soup.new_tag("li")
            a_icon = soup.new_tag("a", href=f"/nyt-crossword-answers-{url_date}/", **{"class": f"icon {icon_class}"})
            a_icon.string = count
            li.append(a_icon)
            ul_stats.append(li)

        # Append span_date and ul_stats to div_info
        div_info.append(span_date)
        div_info.append(ul_stats)

        # Create the p element for article content
        p_content = soup.new_tag("p")
        p_content.string = f"Here are all of the answers for the NYT Crossword on {dotw_string} {month_string} {day_string}, {year_string}"

        # Append header, div_info, and p_content to article
        article.append(header)
        article.append(div_info)
        article.append(p_content)

        # Print the HTML
        print(article)

        # delete the first real article if it is the same date (ie this code ran more than once in a day)
        first_article = articles[1]
        found_url_date = first_article.find_all(string=lambda text: text and url_date in text, recursive=True)
        if (found_url_date):
            print(f"found an article at the top of the home page with url {url_date}. Deleting it...")
            first_article.extract()

        welcome_banner = articles[0]

        #inject article at position 1
        print("inserting article into home page at position 1")
        welcome_banner.insert_after(article)

        # UPDATE WELCOME BANNER DATE
        print("updating welcome banner date")
        welcome_banner_div_info = welcome_banner.find_all('div', **{'class':'info'})[0]
        welcome_banner_date_span = welcome_banner_div_info.find_all('span')[0]
        welcome_banner_date_span.extract()
        welcome_banner_div_info.insert(0, span_date)

        print(f"Putting s3 object with key index.html")
        s3.put_object(
            Bucket=ASSET_BUCKET_NAME,
            Key=f"index.html",
            Body=soup.prettify().encode('utf-8'),
            ContentType='text/html'
        )


def download_template_from_s3(s3, bucket_name, template_path, local_path):
    # Download the file from S3
    try:
        s3.download_file(bucket_name, template_path, local_path)
        print(f"File downloaded successfully from S3 to {local_path}")
    except Exception as e:
        print(f"Error downloading file from S3: {e}")

def handler(event, context):
    # get current date, in appropriate
    current_date = datetime.now()
    # current_date = datetime(year=2024, month=3, day=24)
    current_date_formatted = format_date_for_xword(current_date)
    # Send a GET request to the xword_info webpage
    response = requests.get(XWORD_INFO_URI.format(current_date_formatted))
    print(response)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        answers_data = []
        # Find the container of all 'across' clues and answers
        across_container = soup.find(id="ACluesPan")
        # Find all divs in the container
        across_divs = across_container.find_all("div")
        # Find the container of all 'down' clues and answers
        down_container = soup.find(id="DCluesPan")
        # Find all divs in the container
        down_divs = down_container.find_all("div")
        # generate all clues and answers and aggregate in solution_map
        answers_data = answers_data + create_list_from_divs(across_divs, "across", current_date) + create_list_from_divs(down_divs, "down", current_date)
        print(answers_data)
        print(f"{len(answers_data)} words found from xwordinfo.com for date {current_date}")
        
        s3 = boto3.client('s3')
        # download all template files from s3 locally. will use the local copy for templating 
        download_template_from_s3(s3, ASSET_BUCKET_NAME, CLUE_TEMPLATE_S3_PATH, CLUE_TEMPLATE_LOCAL_PATH)
        download_template_from_s3(s3, ASSET_BUCKET_NAME, PUZZLE_TEMPLATE_S3_PATH, PUZZLE_TEMPLATE_LOCAL_PATH)
        download_template_from_s3(s3, ASSET_BUCKET_NAME, HOME_PAGE_S3_PATH, HOME_PAGE_LOCAL_PATH)

        # Initialize DynamoDB client
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')

        # Iterate over the dictionary and create each clue page
        for clue_data in answers_data:
            print(clue_data)
            dynamo_item = add_clue_to_dynamo(dynamodb, clue_data)
            create_clue_page_html_from_template(s3, dynamo_item)

        # create answer page for the day's puzzle
        create_puzzle_page_html_from_template(s3, answers_data)
        # update home page with link to puzzle page
        update_home_page_html_from_template(s3, answers_data)

        return {
            'statusCode': 200,
            'body': json.dumps(f"${current_date} crossword parsed and uploaded to DynamoDB successfully!")
        }

handler("", "")