# import os
# import requests
# import json
# from .base_tool import BaseTool
# from bs4 import BeautifulSoup

# class SerperDevTool(BaseTool):
#     name: str = "Search the internet"
#     description: str = "A tool for performing a Google search and returning results."

#     def _run(self, search_query: str):
#         url = "https://google.serper.dev/search"
#         payload = json.dumps({"q": search_query})
#         headers = {'X-API-KEY': os.environ['SERPER_API_KEY'], 'Content-Type': 'application/json'}
#         response = requests.request("POST", url, headers=headers, data=payload)
#         return response.text

# class ScrapeWebsiteTool(BaseTool):
#     name: str = "Scrape website content"
#     description: str = "A tool that can be used to scrape a website content."

#     def _run(self, website_url: str):
#         response = requests.get(website_url)
#         soup = BeautifulSoup(response.content, "html.parser")
#         return soup.get_text()