import { NavLink, Route, Routes } from "react-router";

import { ComparePage } from "./pages/ComparePage";
import { EstimatePage } from "./pages/EstimatePage";
import { PricingPage } from "./pages/PricingPage";

export function App() {
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="container site-header-inner">
          <NavLink to="/" className="brand">
            <img src="/favicon.svg" alt="" width={24} height={24} />
            Token Cost Estimator
          </NavLink>
          <nav aria-label="Main">
            <NavLink to="/" end>
              Estimate
            </NavLink>
            <NavLink to="/compare">Compare</NavLink>
            <NavLink to="/prices">Prices</NavLink>
          </nav>
        </div>
      </header>

      <main id="main" className="container">
        <Routes>
          <Route path="/" element={<EstimatePage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/prices" element={<PricingPage />} />
          <Route
            path="*"
            element={
              <header className="page-header">
                <h1>Page not found</h1>
                <p className="lede">
                  <NavLink to="/">Go to the estimator</NavLink>
                </p>
              </header>
            }
          />
        </Routes>
      </main>

      <footer className="site-footer">
        <div className="container">
          Estimates from each provider's published standard prices. Not invoices:
          check the date each price was verified.
        </div>
      </footer>
    </div>
  );
}
