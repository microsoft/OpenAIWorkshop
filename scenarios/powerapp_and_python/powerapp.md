
## Exercise 4: POWER APP

1. Enter the following link in your browser to download **OpenAI-Playground_20230302010547.zip** folder.

```
https://github.com/rcy0228/OpenAIWorkshop/raw/main/scenarios/powerapp_and_python/powerapp/OpenAI-Playground_20230302010547.zip
```

2. Navigate to https://make.powerapps.com/. On **Welcome to Power Apps** select your **Country/Region** click **Get Started**. 

   ![](./images/welcome.png)
    
3. Select **Apps** on the left navigation and click **Import Canvas App**. 

    ![](./images/import-canvas.png)

4. On **Import package** page click on **Upload**.

    ![](./images/upload-importpackage.png)

5. From the **Downloads (1)** select the **OpenAI-Playground_20230302010547.zip (2)** folder you downloaded earlier and click on **Open (3)**.

     ![](./images/upload-openai-playground.png)

6. Once the zip file is uploaded, in the **Review Package Content** for **OpenAI Playground** click on setup icon under **Actions**. 

     ![](./images/review-package-content.png)

7. In the **Import setup** pane select **Create as new** from the drop-down for **Setup**, and click on **Save**.

      ![](./images/import-setup.png)

8.  Repeat Steps 6 and 7 for **Openaisummarization**.

9. Next click on **Import** to import the package into powerapps environment.  

     ![](./images/import-openai-package.png)

10. Once the import is completed, click on **Apps**, then click on `...` next to **OpenAI Playground** and click on **Edit**.

      ![](./images/open-ai-apps.png)

11. You will observe that it has import the Power App canvas app and the Power Automate Flow into the workspace.

      ![](./images/gpt-3.png)

12. To navigate back click on **Back** then click **Leave**.

      ![](./images/exit-openai-powerapp.png)

13. Next select the **Flows** Pane, click on **Edit** for **Openaisummarization**.

      ![](./images/open-ai-flows.png)

14. Edit the Power Automate Flow HTTP step by entering your own Azure OpenAI API **Key** and **Endpoint** and click on **Save**.

      ![](./images/endpoint-key.png)

15. From the **Apps (1)** page click on the **OpenAI Playground (2)** app to run the app.

     ![](./images/runpowerapp-1.png)
