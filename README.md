# Databricks Genie Integration App

A modern Databricks App that integrates with Genie Conversational API to provide an AI-powered interface for data insights and SQL query generation.

## Features

- **Genie Conversational API Integration**: Direct integration with Databricks Genie for natural language data queries
- **Interactive Chat Interface**: User-friendly React-based chat UI
- **SQL Query Display**: View generated SQL queries with syntax highlighting
- **Results Visualization**: Tabular display of query results
- **Session Management**: Maintains conversation context across messages

## Prerequisites

- Databricks workspace with Genie enabled
- Databricks Personal Access Token
- Node.js 18+ and Python 3.9+
- Access to a Genie Space in your Databricks workspace

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/genie-integration-app.git
cd genie-integration-app
```

### 2. Configure environment variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your Databricks configuration:

```env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token
DATABRICKS_GENIE_SPACE_ID=your-genie-space-id
```

**⚠️ IMPORTANT: Security Best Practices**
- **NEVER commit your actual tokens or credentials to version control**
- Keep your `.env.local` file in `.gitignore` (already configured)
- For production deployments, use Databricks secrets or environment variables
- The `app.yaml` file should use placeholders or environment variable references, not actual tokens

**To find your Genie Space ID:**
1. Navigate to your Databricks workspace
2. Open the Genie interface
3. Select or create a Genie space
4. The Space ID is in the URL: `https://[workspace]/genie/rooms/[SPACE_ID]`

### 3. Install dependencies

#### Backend (Python)

```bash
pip install -r requirements.txt
```

#### Frontend (React)

```bash
cd client
npm install
cd ..
```

### 4. Run the application locally

#### Start the backend server:

```bash
uvicorn server.app:app --reload --port 8000
```

#### In a new terminal, start the frontend:

```bash
cd client
npm run dev
```

The app will be available at `http://localhost:3000`

## Deployment to Databricks Apps

### 1. Build the frontend

```bash
cd client
npm run build
cd ..
```

### 2. Deploy to Databricks

```bash
databricks apps deploy --app-name genie-integration-app
```

### 3. Configure environment variables in Databricks

After deployment, set the environment variables in your Databricks App configuration:

1. Go to your Databricks workspace
2. Navigate to Apps
3. Select your deployed app
4. Go to Settings → Environment Variables
5. Add the required variables:
   - `DATABRICKS_GENIE_SPACE_ID`
   - `DATABRICKS_TOKEN` (if not using workspace authentication)

## Project Structure

```
.
├── app.yaml                 # Databricks Apps configuration
├── requirements.txt         # Python dependencies
├── package.json            # Node.js dependencies
├── server/
│   ├── app.py              # FastAPI application
│   └── routers/
│       └── genie.py        # Genie API integration
└── client/
    ├── src/
    │   ├── App.tsx         # Main React component
    │   └── components/
    │       └── GenieChat.tsx  # Chat interface component
    └── dist/               # Built frontend (after npm run build)
```

## API Endpoints

- `POST /api/genie/send-message`: Send a message to Genie
- `GET /api/genie/health`: Check API health and configuration

## Usage

1. Open the application in your browser
2. Type a natural language question about your data
3. Genie will process your request and:
   - Generate appropriate SQL queries
   - Execute the queries
   - Return formatted results
4. View the generated SQL and results in the interface

## Troubleshooting

### Authentication Issues

- Ensure your Personal Access Token has the necessary permissions
- Verify the `DATABRICKS_HOST` URL is correct (no trailing slash)
- Check that the Genie Space ID is valid

### Connection Errors

- Verify your Databricks workspace is accessible
- Check network connectivity and firewall settings
- Ensure Genie is enabled in your workspace

### No Results

- Verify you have access to the tables/schemas Genie is querying
- Check that your Genie space is properly configured with data sources

## License

MIT