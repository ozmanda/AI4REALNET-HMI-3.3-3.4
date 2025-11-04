!! THIS REPO IS DEPRECATED - MIGRATED TO https://github.com/CyberneticLearningSystems/AI4REALNET-HMI-3.3-3.4 !!

# AI4REALNET Augmented Decision-Making HMI

This HMI is developed for augmented human decision making, considering two interaction types: 
1. **Human-AI Co-Learning:** The co-learning interaction mode aims to achieve mutually beneficial interaction between the human and AI agent. 
2. **Autonomous AI:** In the autonomous interaction mode, the human agent acts as a director, providing high-level directives through the HMI to the AI agent, which then executes the directive autonomously.

<img src="src/imgs/HMI_overview.png" alt="HMI Overview" width="600" />

# Installation & Setup

The HMI is programmed with python 3.10.11 using the ``PyQT`` package. The ``app_new.py`` script can be run directly, and allows for the following simulation setup options: 
- Agent model: load an agent model which performs actions in the environment
Steu- Scenario file: load a specific, pre-defined scenario. Scenarios contain specific network topologies, lines and schedules (see the drawing board)
- Environment settings
    - width and height
    - number of agents
    - Malfunction rate
    - Minimum/maximum malfunction duration

<img src="src/imgs/simulation_setup.png" alt="Simulation setup" width="400" />

# Human-AI Co-Learning
Currently, the HMI focuses on human learning and decision support. The functions are divided into Operative and Post-Operative, meaning whether they are used during the operation to actively solve and/or prevent issues, or whether they are used after operations to analyse and reflect on behaviour. 

## Operative Functions
The HMI allows for the operator to interact with the environment and displays train information on request (click on the train) and highlights malfunctioning trains. For malfunctions, two solution options are given - solution formulation or solution generation. 

<img src="src/imgs/train_info.png" alt="Train information window" width="400" /> <img src="src/imgs/malfunction_options.png" alt="Train information window" width="445" />

The solution generation function displays solution suggestions by an artificial agent, whereas the solution formulation allows the human agent to formulate their own solution. Currently, the idea is to have this be in text form, then translated into actions using a RAG (@reno) - WIP. 

<img src="src/imgs/solution_generation.png" alt="Solution generation window" width="350" /> <img src="src/imgs/solution_formulation.png" alt="Solution formulation window" width="350" />

Each solution can then either be directly executed or first analysed. The analysis window presents general risk assessment, the number of sub-actions required for the solution and the number of trains impacted by the solution. Additionally, the predicted impact of this solution on the trains is presented.

<img src="src/imgs/solution_analysis.png" alt="Solution analysis window" width="350" />

## Post-Operative Functions
After operations, the co-learning system supports human learning with the ability to analyse and reflect on incidents and the decisions made. At the end of the simulation, the operator is presented with a list of the incidents which occurred, and can double-click on an incident to further analyse the decisions taken. 

<img src="src/imgs/incident_review1.png" alt="Solution analysis window" width="350" />

Upon choosing an incident to review, a similar window is opened as when solutions are analysed. The key difference in the post-operative case is that the impacted trains and the delays are no longer predicted, but actual delays. 


<img src="src/imgs/incident_review_2.png" alt="Solution analysis window" width="300" /> <img src="src/imgs/reflection_module.png" alt="Solution analysis window" width="380" />

The operator is also given the opportunity to reflect on the incident and is prompted to answer a series of questions that support active learning. WIP: log and summarise this reflection to support knowledge-sharing across incidents and operators. 


<img src="src/imgs/simulation_setup.png" alt="Simulation setup" width="400" />

# Autonomous AI & Human Director
The "director mode" of the HMI is currently WIP, but will support the following interaction modes: 
1. **Directive Input:** the human agent can formualte a high-level input which is executed autonomously by the autonomous agent
2. **Negotiation:** should conflicts occur during execution of the directives or as a result of disruptions in the network, the agents autonomously negotiate the best course of action, which is then reported to the human agent.
