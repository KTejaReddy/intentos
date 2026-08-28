# Hackathon Demo Checklist

To guarantee a flawless live demonstration of IntentOS, please follow this checklist precisely:

- [ ] **Reset State**: Ensure all previous generated artifacts in `data/projects/` are cleared.
- [ ] **Start Backend**: Run `uvicorn app.main:app --reload` in the `backend/` directory.
- [ ] **Start Frontend**: Run `npm run dev` in the `ide/` directory.
- [ ] **Open Browser**: Navigate to `http://localhost:5173`.
- [ ] **Theme Check**: Confirm the IDE is rendering the dark glassmorphism theme correctly.
- [ ] **Live Prompt**: In the natural language bar, type: *"Create a Library Management System."*
- [ ] **Show Pipeline Visualizer**: After compilation, immediately open the bottom panel and show the Judges the `Tokens`, `AST`, and `Benchmarks` tabs to prove the generation was instantaneous and not hallucinated.
- [ ] **Run Generated App**: Open a terminal, navigate to the newly generated project folder, and run the FastAPI server to show the live application working.
- [ ] **Demonstrate Errors**: Intentionally inject a typo into the IntentLang (e.g., reference a Model that doesn't exist) and hit compile to show the Semantic Analyzer catching the error instantly.
