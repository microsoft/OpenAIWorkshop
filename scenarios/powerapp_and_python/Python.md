## Exercise 4b: Build Open AI application with Python

1. Search and select **Azure Synapse Analytics** in the azure portal.

      ![](images/p2.png)

1.  On the **Overview** blade under **Getting started** section, click **Open** to open Synapse Studio.
     
    ![](images/open-workspace.png)
    
1. Click on **Develop (1)** then click on **+ (2)** and select **Import**.

    ![](images/import-note.png)

1. Navigate to `C:\labfile\OpenAIWorkshop\scenarios\powerapp_and_python\python` location and select `OpenAI_notebook.ipynb`, then click on **Open**.

     ![](images/notebook.png)

1. Select **openaisparkpool** from the drop-down menu of **Attach to**.

    ![](images/openai-sparkpool.png)

1. Run the notebook it step by step to complete this exercise. Click on **Run** button next to the cell. 

     ![](images/run.png)

1. In **2. Import helper libraries and instantiate credentials** replace the **AZURE_OPENAI_API_KEY** and **AZURE_OPENAI_ENDPOINT** with your API key and End point URL.

    ![](images/key-endpoint.png)
   
   From Azure Portal, navigate to **openaicustom-XXXXXX** Resource group, and Select Azure OpenAI resource.
    ![](images/Ex4b-S7.1.png)

   Under Resource Management, select **Keys and Endpoint (1)** , copy **Key 1 (2)** and **Endpoint (3)** and replace the **AZURE_OPENAI_API_KEY** and **AZURE_OPENAI_ENDPOINT** with your API key and End point URL in the script.

    ![](images/Ex4b-S7.2.png)
     
    > **Note:** If you encounter an error "Openai module not found", enter `%` in before the **pip install** in the Install OpenAI cell and re-run the notebook again.

1. For **2. Choose a Model**, replace **model** value from **text-curie-001** to **demomodel**.

    ![](images/choosemodel.png)

1. In **temperature**, replace **engine** value from **text-curie-001** to **demomodel**.

     ![](images/temp.png)

1. In **top_p**, replace **engine** value from **text-curie-001** to **demomodel**.

     ![](images/top-p.png)

1. For **n**, replace **engine** value from **text-curie-001** to **demomodel**.

     ![](images/n.png)

1. In **logprobs**, replace **engine** value from **text-curie-001** to **demomodel**.

     ![](images/logprobs.png)

1. After running the notebook successfully, click on **Publish all**.

     ![](images/publish.png)

1. Then click on **Publish** to save the changes. 

    ![](images/publish-1.png)
