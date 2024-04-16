![image](https://github.com/Nathan-Roll1/gpt-fuego/assets/96995554/499fe231-6a6c-4c75-bdc7-b8eb96980be1)


![GPT-fuego Demo](gpt-fuego-demo.gif)

## About GPT-fuego

`gpt-fuego` is a cutting-edge agent designed to enhance the capabilities of Large Language Models (LLMs) through a unifying interface that integrates various generative operations. It combines speacialized fine-tuning with zero-shot calls to let users chat with SQL databases and external data APIs simultaneously. Built with Streamlit, Replit, and OpenAI.

## Features

- **Enhanced Generative Operations**: GPT-fuego brings together a wide range of generative techniques to foster innovation in the field.
- **User-friendly Interface**: Designed with the end-user in mind, the framework offers an intuitive interface for seamless integration into existing projects.
- **Scalability**: Built to scale, GPT-fuego supports projects ranging from small-scale experiments to large, complex applications.
- **Open Source**: GPT-fuego is open source, encouraging contributions and modifications from the global developer community.

## Fine-Tuning
Publicly available data science notebooks from kaggle are used to generate a custom dataset of paired markdown/code (treated as chat/response) cells. `gpt-fuego` uses this dataset to fine-tune and validate gpt-3.5-turbo.

## Architecture
1. **Initial Prompt**: The process begins with the user inputting a prompt.
   
2. **Scrubbed Prompt**: 
   - The prompt is then scrubbed to remove details that are not handled by the core model, ensuring only relevant information is processed.

3. **SQL Request**:
   - A SQL request is sent to BigQuery to retrieve necessary data, laying the groundwork for the model's input.

4. **Parallelized Processing**:
   - The core of the processing happens here, where parallelized calls are made to:
     - A fine-tuned model for tailored responses.
     - Code validation to ensure accuracy and reliability.
     - Execution to generate the response based on the model's output and validation checks.

5. **Package Response**:
   - The output from the previous step is then packaged into a coherent response, ready for delivery.

6. **API Router**:
   - The initial prompt is run through an API router, which determines if further API calls are necessary based on the request's specifics.

7. **Optional API Call**:
   - If required, an external API call is made at this stage to enrich the response or perform additional computations.

8. **Return Packaged Response**:
   - Finally, the packaged response, now possibly enhanced with API call results, is returned to the user.

![image](https://github.com/Nathan-Roll1/gpt-fuego/assets/96995554/1558b5ec-535d-46a4-8348-5e7af5320241)


SQL database connection (part 2) and external data API (part 3) are built into the original fine-tuned model pipeline.
![image](https://github.com/Nathan-Roll1/gpt-fuego/assets/96995554/33c77905-9b29-4e19-8c29-2d4dbd94da4a)

