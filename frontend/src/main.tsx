import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

class Boundary extends React.Component<{ children: React.ReactNode }, { err: Error | null }> {
  state = { err: null as Error | null };
  static getDerivedStateFromError(err: Error) { return { err }; }
  render() {
    if (!this.state.err) return this.props.children;
    return <div style={{ padding: 40, maxWidth: 560 }}><h2>Something went wrong on this page</h2><p className="muted">{this.state.err.message}</p>
      <a className="btn" href="/">Back to start</a></div>;
  }
}
ReactDOM.createRoot(document.getElementById("root")!).render(<Boundary><BrowserRouter><App /></BrowserRouter></Boundary>);
