# 🌱 TerraPulse

### Atmanirbhar Krishi. Atmanirbhar Bharat.
**Intelligent Agricultural Decision Support. Built for the Fields.**

TerraPulse is an intelligent agricultural decision-support platform designed to help farmers, Farmer Producer Organizations (FPOs), and agricultural professionals make informed decisions through environmental intelligence, scientific crop simulation, weather forecasting, and interactive farm visualization.

By integrating weather data, soil information, crop science, and AI-powered analysis, TerraPulse transforms complex agricultural information into practical, understandable, and actionable insights.

**Our principle: The farmer should never have to adapt to TerraPulse. TerraPulse should adapt to the farmer.**

---

## 🌾 The Problem

Agricultural decisions depend on several interconnected factors:

- Changing weather conditions and rainfall variability.
- Soil characteristics and moisture availability.
- Crop selection and growth stages.
- Irrigation requirements and water availability.
- Environmental uncertainty and future climate conditions.
- Potential crop stress and agricultural risks.

However, farmers often rely on disconnected information sources, fragmented tools, and complicated technical reports to make these decisions.

TerraPulse addresses this challenge by bringing environmental data, agricultural science, and decision-support capabilities into one unified platform.

## 💡 Our Solution

TerraPulse is built around three core capabilities:

| Capability | Purpose |
|---|---|
| **Simulation** | Evaluate crop growth and water-related outcomes using scientific agricultural models. |
| **Future Fold** | Explore multiple possible environmental trajectories and compare their implications for agricultural decisions. |
| **AI Analysis** | Translate agricultural information and scientific outputs into understandable, data-grounded insights. |

---

## 🎯 Core Features

### 1. Living Field — Interactive 3D Farm Visualization

Living Field provides an interactive representation of agricultural land through a three-dimensional digital environment.

Capabilities include:

- Realistic 3D agricultural terrain.
- Crop plots and cultivation patterns.
- Interactive field inspection.
- Soil moisture visualization.
- Irrigation zones and water distribution.
- Crop-health visualization where supporting data is available.
- Weather and terrain visualization layers.
- Camera rotation, zoom, and pan controls.

Living Field connects visual representations with agricultural data rather than functioning as a decorative 3D scene.

### 2. Scientific Crop Simulation

TerraPulse incorporates established agricultural modelling methodologies to evaluate crop and water-related outcomes.

Scientific foundations include:

- FAO-56 reference evapotranspiration methodology.
- AquaCrop-based crop growth and water productivity modelling.
- Soil and environmental input parameters.
- Crop-specific parameters and growth characteristics.
- Water balance and irrigation-related calculations.

### 3. Future Fold — Explore Possible Futures

Agriculture involves uncertainty. A single weather forecast cannot represent every possible future condition.

Future Fold is designed to:

- Explore multiple possible weather trajectories.
- Compare environmental scenarios.
- Evaluate potential crop and water-related implications.
- Understand uncertainty in future conditions.
- Support irrigation and crop-risk planning.

Each environmental trajectory should remain associated with its corresponding simulation inputs.

### 4. AI-Powered Agricultural Analysis

The AI analysis layer makes agricultural information easier to understand.

It is designed to provide:

- Explanations of field conditions.
- Summaries of crop and environmental risks.
- Contextual irrigation insights.
- Interpretations of scientific simulation results.
- Actionable recommendations grounded in available information.

AI-generated insights must remain consistent with actual data, model outputs, and documented assumptions.

### 5. Farmer-Centric Interaction

TerraPulse is designed around different levels of technological familiarity.

**Connect**
- Simplified farmer-facing interactions.
- Voice-friendly workflows.
- Local-language accessibility.
- Cached information for limited-connectivity situations.

**Assisted**
- Workflows for FPO representatives and agricultural field workers.
- Assisted field-data collection and interpretation.
- Support for communicating agricultural insights to farmers.

**Observatory**
- Detailed analytical environment.
- Living Field visualization.
- Farm Timeline.
- Future Fold scenario exploration.
- Scientific and environmental insights.

---

## 🏗️ System Architecture

TerraPulse follows a modular architecture separating user interaction, environmental data retrieval, crop intelligence, scientific simulation, and AI analysis.

```text
                       TERRAPULSE
                            |
              +-------------+-------------+
              |             |             |
           Connect       Assisted     Observatory
              |             |             |
              +-------------+-------------+
                            |
                     Frontend Layer
                            |
                       Backend APIs
                            |
          +-----------------+-----------------+
          |                 |                 |
      Weather Data       Soil Data        Crop Data
          |                 |                 |
          +-----------------+-----------------+
                            |
                  Environmental Inputs
                            |
                  Scientific Simulation
                            |
                  +---------+---------+
                  |                   |
              Simulation          Future Fold
                  |                   |
                  +---------+---------+
                            |
                       AI Analysis
                            |
                  Agricultural Insights
                            |
                     Decision Support
```

### Architectural Components

| Component | Responsibility |
|---|---|
| Frontend | User interface, dashboard, visualization, and interactions. |
| Backend | API endpoints, service coordination, and data processing. |
| Weather Services | Weather retrieval, normalization, and ensemble information. |
| Soil Services | Soil properties and moisture information. |
| Crop Data Layer | Crop identity resolution, parameters, and agricultural references. |
| Simulation Engine | Scientific crop and water-related calculations. |
| Future Fold | Environmental scenario exploration and comparison. |
| AI Analysis | Grounded interpretation of agricultural data and simulation outputs. |
| Living Field | Interactive visualization of field geometry and supported agricultural data layers. |

---

## 🧪 Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript |
| 3D Visualization | Three.js, React Three Fiber, Drei |
| Backend | Python |
| Scientific Simulation | AquaCrop-OSPy, FAO-56 methodology |
| Weather Intelligence | Open-Meteo |
| Soil Information | SoilGrids |
| Crop References | FAO AGROVOC, ECOCROP |
| Biodiversity References | GBIF |
| Version Control | Git, GitHub |

*Refer to the actual dependency files for the exact currently installed libraries and versions.*

---

## 🌍 Data Sources and Scientific References

| Source | Purpose |
|---|---|
| [Open-Meteo](https://open-meteo.com/) | Weather information, forecasts, and ensemble data. |
| [ISRIC SoilGrids](https://soilgrids.org/) | Modelled soil property information. |
| [FAO AGROVOC](https://www.fao.org/agrovoc/) | Agricultural terminology and crop identity references. |
| [FAO ECOCROP](https://ecocrop.review.fao.org/) | Crop environmental requirements and references. |
| [GBIF](https://www.gbif.org/) | Biodiversity and species reference information. |
| [FAO-56](https://www.fao.org/4/x0490e/x0490e00.htm) | Reference evapotranspiration methodology. |
| [FAO AquaCrop](https://www.fao.org/aquacrop/) | Crop response to water and agricultural simulation methodology. |

### Data Integrity Principles

- Preserve the source and provenance of retrieved information.
- Distinguish measured, estimated, forecast, and simulated values.
- Never interpret missing data as zero.
- Do not present modelled soil properties as live field measurements.
- Maintain consistency between weather ensemble members and corresponding simulation inputs.
- Clearly identify illustrative and demonstration data.
- Ground AI-generated insights in available data and scientific outputs.

---

## 📁 Project Structure

```text
TerraPulse/
│
├── apps/
│   └── web/                 # Frontend application
│
├── backend/                 # Backend services
│
├── tests/                   # Automated tests
│
├── docs/                    # Technical documentation
│
├── README.md
├── .gitignore
└── ...
```

*This is a conceptual overview. Refer to the actual repository for the current directory structure.*

---

## ⚙️ Getting Started

### Prerequisites

- Git
- Node.js
- npm
- Python version supported by backend dependencies
- Visual Studio Code or another code editor

### 1. Clone the Repository

```bash
git clone <YOUR_TERRAPULSE_REPOSITORY_URL>

cd TerraPulse
```

### 2. Install Frontend Dependencies

```bash
cd apps/web
npm install
```

### 3. Start the Frontend

```bash
npm run dev
```

Open the local development URL displayed in your terminal.

### 4. Set Up the Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies if a `requirements.txt` exists:

```bash
pip install -r requirements.txt
```

Start the backend using the entry point and command specified in the backend configuration.

*Verify the actual directory structure, dependency files, environment variables, and startup commands before running the application.*

---

## 👥 Development Workflow

TerraPulse is developed collaboratively using Git and GitHub.

Recommended workflow:

1. Synchronize with the appropriate integration branch.
2. Create a dedicated feature branch.
3. Work within the assigned module.
4. Follow existing coding conventions and API contracts.
5. Run relevant tests and validation checks.
6. Commit changes with meaningful messages.
7. Push the feature branch.
8. Submit a pull request for review and integration.

Example:

```bash
git checkout main
git pull origin main

git checkout -b feature/your-feature-name

git add <your-files>
git commit -m "feat: describe your implementation"

git push -u origin feature/your-feature-name
```

Avoid overwriting or merging unfinished work from other contributors.

---

## 🔬 Testing and Validation

Each module should be validated independently before integration.

Recommended validation areas:

- Frontend build and TypeScript checks.
- Backend unit tests.
- API contract validation.
- Weather service validation.
- Soil data validation.
- Crop identity and parameter validation.
- Scientific simulation input validation.
- Weather ensemble consistency.
- 3D visualization and interaction testing.
- Missing-data and error-state handling.

Scientific outputs should be evaluated against expected inputs, model assumptions, and documented methodology.

---

## 🚀 Project Vision

TerraPulse aims to bridge the gap between agricultural science and practical farming decisions.

Instead of presenting farmers with disconnected datasets, complicated charts, or unexplained predictions, TerraPulse connects field conditions, crop science, environmental intelligence, and simulation-driven insights.

Our vision is to create an agricultural decision-support environment where farmers, FPOs, and agricultural professionals can:

- Understand their land.
- Explore crop and soil conditions.
- Evaluate irrigation requirements.
- Understand environmental uncertainty.
- Compare possible agricultural outcomes.
- Make better-informed decisions.

**TerraPulse — Turning agricultural intelligence into actionable decisions.**

---

## 🤝 Contributing

Contributions are welcome from developers, researchers, agricultural professionals, and technology enthusiasts.

When contributing:

- Keep modules independent and reusable.
- Follow existing coding conventions.
- Preserve API contracts.
- Document external data sources.
- Validate scientific assumptions.
- Include appropriate tests.
- Respect existing team ownership and integration workflows.
- Submit changes through pull requests.

---

## 📜 License

The project licence should be specified through a dedicated `LICENSE` file.

Third-party datasets, models, libraries, and 3D assets remain subject to their respective licences and attribution requirements.

---

<p align="center">

# 🌱 TerraPulse

**Atmanirbhar Krishi. Atmanirbhar Bharat.**

*Intelligent Agricultural Decision Support. Built for the Fields.*

</p>
