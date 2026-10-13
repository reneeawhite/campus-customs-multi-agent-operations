# AI Prompts

## Problem 1: Vibe coder prompts

### Prompt 1 (verbatim)

```text
I’m working on “Problem 1: Vibe coder prompts”. Create AI_prompts.md and keep it updated as I work. This file will be a log of what I types word-for-word to my vibe coder. Each problem will have its own section and must include the following:

- The problem number and title
- At least one prompt I types, word-for-word

• One follow-up prompt if needed, word-for-word, and then one sentence on what was lacking after the first
```

### Follow-up prompt

None needed so far.

## Problem 2: Study the Campus Customs database

### Prompt 1 (verbatim)

```text
Now I'm working on "Problem 2: Study the Campus Customs database”. Help me look through every table and its fields. Show the three open tickets to me so I understand how they link to other tables. Also, start output/harness.md. For each table, list the fields and add one short line on why that table matters for the agents. This harness file will keep growing in later problems
```

### Follow-up prompt

```text
Also, I meant to put desk.date_today so you can updata that in harness.md
```

The first pass incorrectly described `data_today` as wording from the assignment; it missed that you intended `desk.date_today`.

## Problem 3: Build the MCP server

### Prompt 1 (verbatim)

```text
Now I’m working on “Problem 3: Build the MCP server”. Write an MCP server in mcp_server/ using FastMCP, which will talk to data/campus_customs_new\.db. I don’t need to connect for run it in this problem. Every agent that I mentioned earlier in this homework will use the tools in this MCP server. I will add more tools to it later. Right now write three tools I that I will need for the tickets in the database. Make sure to keep the names clear, and never invent any data, only use information in the database.

In output/harness.md, list each my three MCP tools. For every tool include the following:

- Which table it reads
- Which ticket it helps unlock (101, 102, or 103), and
- One sentence on why that tool is the right one for that ticket

Do not use poor reasoning in the sentence like “reads inventory”. Including results like these are too vague and will give me a low score in this homework, so make sure to tie the tool to the ticket. Also, add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has
```

### Follow-up prompt

None needed so far.

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt 1 (verbatim)

```text
Now I’m working in “Problem 4: Add the MCP server to vibe coder and test each tool”. I need to add my MCP server to this project so that the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root (or however Codex save the local MCP server lists. With Codex connected, I will need to test each of the three MCP tools. Make sure to save the evidence in output/mcp_smoke.json. For every tool include the following:

- The prompt I asked Codex (what do I ask?)
- The tool name

• The tool output (must match the values in data/campus_customs_new\.db
```

### Follow-up prompt (verbatim)

```text
Ok, now I'm just going to run each of the prompts to check. Please use the get_customer_order_context MCP tool for ticket 101 and report its linked stock, pricing, invoice, vendor, and shop date.
```

The initial request described saving MCP smoke-test evidence but did not provide a concrete ticket-level prompt with the facts to verify.

## Problem 5: Build the agent team and grow the MCP tools

### Prompt 1 (verbatim)

```text
Now I’m working on “Problem 5: Build the agent team and grow the MCP tools”. I need to build the agentic team for Campus Customs using PydanticAI: (1) Boss, (2) Inventory, (3) Accounting, (4) Facilities, and (5) Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. Add the agent prompts to backend/prompts/ and have one file per agent. Put data types in backend/models.py, and the agent files under backend/ (make sure the layout/organization of the five roles are clear). As stated before use my PORTKEY_API_KEY and make sure only get-6-luna is used for every agent.

Help me edit the shop rules I listed previously into prompts for each agent so that it is more detailed and covers all aspects of an agent’s work and scope. Please make sure it is detailed because for this problem, a more detailed scope will score higher than a short generic prompt.

Make sure to add any tools that the agent needs to my MCP server so that they can work on open tickets. The shop facts will come over from the MCP server data/campus_customs_new\.db, so don’t invent a second shop-tools layer that bypasses MCP. Also, wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. Append this file, do not wipe it each run.

In output/harness.md, list each agent and each MCP tool (including the ones added in this problem) along with which table the tool uses. Also now add a safety section including the following:

- The guardrails a real business would want when agents touch real customers an real money (be very careful and don’t break any rules)
- Plus limits that keep token use in check (I.e. make sure to always use get-6-luna for every agent)

Update mcp_server/README.md so the tool list matches what I have now
```

### Follow-up prompt

```text
can you make sure the prompts have a general understanding as well, so that for future ticekets the agents know which tools to use?
```

The first version tied tool selection to sample ticket IDs and did not clearly explain how to select tools by ticket type for future tickets.

## Problem 6: Plan the three tickets

### Prompt 1 (verbatim)

```text
Now time to work on “Problem 6: Plan the three tickets”. Before I wire the backend I need to write down what I expect the team to do on each open ticket (don’t do it for me, I will need to type this out). Build output/desk_tickets.html as a page that I can double-click with one tab per ticket (101, 102, and 103). Also, add an empty Cash and Reflection tabs for later problems (leave them blank with just a short “coming later” note for now). One each ticket tab, I will fill out an Expected section (by myself but you can create a header, and also add an Actual section/header that you can fill after I run the agents). As stated, I will fill out the expected myself in my own words but include the following subsections for me to fill out:

- Who the boss should call first, and why
- All the agent delegations I expect
- Which MCP tools I expect that run to use

As you help me build the blank template for this problem keep in mind that plans that send every specialist on every ticket will score low, I will need to compare this plan to what actually happens when my agents resolve the three tickets
```

### Follow-up prompt

None needed so far.

## Problem 7: Backend routes

### Prompt 1 (verbatim)

```text
Now I’m working in “Problem 7: Backend routes”. I will be making a React frontend dashboard in problem 8, which needs a backend it can call. In backend/main.py use FastAPI and add routes that do the following:

- Return the three tickets and whether each is open or resolved
- Take a ticket id and run the agent team on that ticket
- Return recent agent events: what each agent said and which tools they used (so the board can refresh)
- Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
- Return the current checking balance from cash_accounts
- Reset the database to the original values when you want to try a fresh run

From the backend/ folder, I should be able to start the server with:

uvicorn main:app --reload --port 8000

(This needs to run in my terminal or I will get zero points for this problem). This should turn on my backend at [http://localhost:8000](http://localhost:8000) so the frontend dashboard can call these routes. In output/harness.md, list each route in one line (what URL / what it does)
```

### Follow-up prompt

None needed so far.

## Problem 8: Agent dashboard

### Prompt 1 (verbatim)

```text
Now I’ll be working in “Problem 8: Agent dashboard”. Help me build the frontend dashboard in frontend/ with React + Vice + Typescript. The page should call the routes I built in Problem 7. At a minimum the board should:

- List all three tickets
- Let me pick on ticket and start the agent team on it
- Show each agent and what they are saying / doing while the ticket runs
- Mark a ticket resolved when the run finishes
- Show a short summary of what each agent did on that ticket
- Let a human approve a pay or purchase when asked
- Show the checking balance (it should drop after an approved pay)

Make this dashboard look cute and cozy like a mom and pop shop feel where the boss is an apple and all of the agents (inventory, accounting, facilities, customer service) are different types of fruits which have unqique identifiers for their agent type. The vibe of the dashboard should take inspiration from the attached image, think of an old country/local market/mom&pop shop. Make sure the dashboard looks really good, and put some intentionality into the layout and feel based on what I’ve told you.

Tell the frontend to talk to the back end at [http://localhost:8000](http://localhost:8000). On the backend allow the Vite page origin (usually, [https://localhost:5173](https://localhost:5173)) so the browser is allowed to call those routes. The board needs to start with “npm run dev” in the terminal (don’t do it yet I want to do it by myself). This should open the react desk in my browser so that I can pick tickets and watch agents. Write output/design.md with what I choose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why. Include my creative choices the make it feel special and something humans would actually enjoy using.
```

The prompt included the attached Mom and Pop's Country Store image for visual inspiration.

### Follow-up prompt (verbatim)

```text
actually make the boss a bulldog like handsome dan and the other agents different types of dogs (golden retrievers, cockerspaniel, terrier, german shepard). And make the dogs look really cool and illustrated
```

The first version used fruit badges and did not provide the illustrated dog identities you wanted.

## Problem 9: Resolve the tickets

### Prompt 1 (verbatim)

```text
Now I’m working on “Problem 9: Resolve the tickets”. Before I test the agents on a full run over the three tickets, reset the working database data/campus_customs_new\.db again so I can start clean. Note the starting checking balance. Then run all three tickets on the board (101, 102, 103) until each is resolved. Open output/desk_tickets.html from Problem 6. On each ticket tab, fill the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep my expected section so I can compare the two (data_tickets_plan has my expected tabs filled out not desk_tickets so I guess merge them so desk_tickets has the expected tabs filled out). On the cash tab of output/desk_tickets.html , itemize the money:

- Starting checking balance (after the reset)
- For each ticket: how cash changed when that ticket resolved, and why (which pay / purchase, dollar amount)
- Ending checking balance - it must match cash_accounts in the working database

Wrong cash math losses points even if the board shows every ticket resolved (so make sure all math is right). Also save:

- Output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
- Output/resolved_board.html - a page I can double click with a screen shot of my React board for each resolved ticket (101, 102, 103)

Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules
```

### Follow-up prompt (verbatim)

```text
I have made approvals for the tickets can you update that in the Actual section for the tickets on the html?
```

The Actual sections still showed the invoice and rent payments as pending and ticket 102 as open after the human approvals were recorded.

## Problem 10: Reflection tab

### Prompt 1 (verbatim)

```text
Now I’m working on “Problem 10: Reflection tab”. Put my following reflection in the reflection tab in the html and organize in a detailed and thorough way keeping my ideas unless where I ask you to check my work and if something else makes more sense)

- “(a) How would you evaluate the performance of the agents on each ticket and why? (b) For each ticket, how did the actual compare to the expected plan you wrote earlier?

Ticket 101a: For Ticket 101, the agents are working well together and fastest, finishing their work in under a minute. The boss is able to call in the different specialists at the beginning which is interesting, but I like that the boss waits until the end to get all of the specialist notes together.

Ticket 101b: I was right in assuming that the Boss would call in accounting first, however, missed that they would also need customer service to draft a message to the human to pay the overdue $840. Also, I listed all of the correct MCP tools used, but in the actual run the different agents used different tools so it was nice that the in the “Actual” section that was clarified.

Ticket 102a: For Ticket 102, the agents also worked fast and in this one facilities and accounting work together more back-to-back, which is different than the previous ticket. I think this shows good performance because the agents don’t have to involve the boss for each step but are able to work through problems together.

Ticket 102b: I was right again that the boss was delegate tasks to facilities and then accounting. However, before doing so it does appear that the boss reviews the context of the ticket himself first, which shows good performance. Again, I listed all of the correct MCP tools used, but not the tools the agents each use individually.

Ticket 103a: For Ticket 103, the agents again worked fasted even though this ticket appears complex with a lot of back and forth between the boss and the agents and amongst the agents. For this ticket the boss had to call of the agents one-by-one and then they were able to collaborate together; similar to how the other tickets operate.

Ticket 103b: I was right once more that the boss was going to call inventory and then accounting again; however, again missed the customer service element. Also, like Ticket 102, the boss heavily reviews the context itself first before delegating tasks. For the MCP tools, along with not allocating tools for each agent, I missed that Inventory would use the list_vendor_capabilities tool.

- What would have been simpler as on agent with tools - and why?

What would have been simpler on agent and tools would probably be inventory, facilities and accounting because there seems to be a lot of back and forth between these agents and so could have been consolidated into one role. Because accounting is handling cash flows and margins which will always impact/influence inventory and Facilties. Customer Service should probably still be its own agent to bring all of the data together (or this could even be consolidated with the Boss role, if not too busy but they probably are)

- Describe 3 new problems Campus Customs might face that this agent team could solve with the tolls you built: (double check that the shop would be able to face and solve these types of tickets)
  - Customer receiving the wrong order and looking to exchange (and if that would come with any price difference, where cost would be more)
  - If you were undercharged on rent and you actually owe more money
  - If a vendor wants to sell you more product to stock in the inventory

- Describer three new problems that campus customs could not solve with the tools you’ve built, and explain the tools and agents you would need to solve them: (help me edit this or find new examples if these are not good; double check that the shop would be able to face and solve these types of tickets)
  - Customer receiving the wrong order and looking to exchange (and if that would come with any price difference, where cost was less so they required a refund)
    - Would need a tool that would be able to handle money coming in (since right now money can only go out)
  - A customer requesting to buy a lease from the store to have a space to sell their own product
    - Again would be sending money into the shop so would need a tool to assess that, as well the least request
  - A investor contacting the store to review their revenue and profit because they are interested in investing
- would need a tool that counts money coming to calculate revenue and the profit because the accounting agent already knows the money going out)

For every answer I just gave tie it to my app and the three tickets I ran, use the ticket and cash tab on the same page as my evidence. Make sure to keep my ideas but help make it better/detailed since my homework problem says generic AI essays without Campus Customs details will score low
```

### Follow-up Prompt (verbatim)

```text
For number three it seems like the first 2 problems aren't new but are exactly like some of the tickets provided. Can you help me craft two new problems and update the html?
```

The earlier examples reused the invoice, rent, and restock scenarios from Tickets 101–103 instead of giving distinct new situations the app could help analyze.
