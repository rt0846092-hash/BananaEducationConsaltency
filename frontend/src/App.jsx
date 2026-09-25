import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import Logo from "./components/Logo";
import Home from "./pages/Home";
import Apply from "./pages/Apply";
import CountryPage from "./pages/CountryPage";
import StaffLogin from "./pages/StaffLogin";
import StaffDashboard from "./pages/StaffDashboard";
import LeadDetail from "./pages/LeadDetail";
import Team from "./pages/Team";
import Reports from "./pages/Reports";
import ChangePassword from "./pages/ChangePassword";
import AddStudent from "./pages/AddStudent";
import Privacy from "./pages/Privacy";
import { clearToken, getToken, staffApi } from "./auth";
import { useT } from "./i18n";
/* global __SAMPLE_NOTICE__ */
import { OFFICE } from "./config";

/**
 * Keeps signed-out people off the staff pages. This is convenience, not
 * security — it only hides screens. The real protection is the queryset
 * filter on the server, which is why a counsellor's API call returns four
 * students and not twelve no matter what the browser does.
 */
function RequireLogin({ children }) {
  return getToken() ? children : <Navigate to="/staff/login" replace />;
}

function PublicHeader() {
  const { t } = useT();
  return (
    <header className="border-b border-rule bg-white">
      <div className="wrap flex items-center justify-between gap-4 py-4">
        <Link to="/" className="flex items-center gap-2.5">
          <Logo className="h-8 w-8" />
          <span className="font-display text-lg font-semibold text-navy-deep">
            {OFFICE.name}
          </span>
        </Link>
        <div className="flex items-center gap-5">
          <a href={`tel:${OFFICE.phoneTel}`} className="hidden text-sm font-medium text-navy hover:text-grass sm:inline">
            {OFFICE.phone}
          </a>
          <NavLink to="/apply" className="btn-go px-4 py-2 text-sm">
            {t("Free counselling")}
          </NavLink>
        </div>
      </div>
    </header>
  );
}

function StaffHeader() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [me, setMe] = useState(null);
  const token = getToken();

  // Hiding the owner links is courtesy, not security — the endpoints behind
  // them return 403 to anyone who isn't an admin.
  //
  // Re-check whenever the token changes. The header stays mounted from the
  // login page onwards, so fetching only once left the owner with no Team or
  // Reports links after signing in, and showed the previous person's links
  // after someone else signed in on the same computer.
  useEffect(() => {
    if (!token) {
      setMe(null);
      return;
    }
    staffApi.me().then(setMe).catch(() => setMe(null));
  }, [token, pathname]);

  const tab = ({ isActive }) =>
    `text-sm ${isActive ? "text-white" : "text-white/70 hover:text-white"}`;

  return (
    <header className="border-b border-rule bg-navy-deep">
      <div className="wrap flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-3.5">
        <div className="flex items-center gap-6">
          <Link to="/staff" className="flex items-center gap-2.5">
            <Logo className="h-7 w-7" tile={false} />
            <span className="font-display font-semibold text-white">Staff area</span>
          </Link>
          {me && (
            <nav className="flex items-center gap-5">
              <NavLink to="/staff" end className={tab}>Students</NavLink>
              {me.is_admin && <NavLink to="/staff/team" className={tab}>Team</NavLink>}
              {me.is_admin && <NavLink to="/staff/reports" className={tab}>Reports</NavLink>}
            </nav>
          )}
        </div>
        <div className="flex items-center gap-5">
          <Link to="/staff/password" className="text-sm text-white/70 hover:text-white">
            Password
          </Link>
          <Link to="/" className="text-sm text-white/70 hover:text-white">
            View the site
          </Link>
          {token && (
            <button
              onClick={() => {
                clearToken();
                setMe(null);
                navigate("/staff/login");
              }}
              className="text-sm text-white/70 hover:text-white"
            >
              Sign out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

function NotFound() {
  const { t } = useT();
  return (
    <div className="wrap max-w-prose py-24 text-center">
      <h1 className="text-3xl">{t("We couldn't find that page")}</h1>
      <p className="mt-3 text-navy-soft">
        {t("The link may be old or mistyped. You can still talk to a counsellor for free.")}
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link to="/apply" className="btn-go">{t("Free counselling")}</Link>
        <Link to="/" className="btn-quiet">{t("Home page")}</Link>
      </div>
    </div>
  );
}

function PublicFooter() {
  const { t } = useT();
  return (
    <footer className="mt-20 border-t border-rule bg-navy-deep text-white/80">
      <div className="wrap grid gap-8 py-12 sm:grid-cols-3">
        <div>
          <Logo className="mb-3 h-9 w-9" tile={false} />
          <h3 className="mb-2 text-white">{OFFICE.name}</h3>
          <p className="text-sm leading-relaxed">
            {t("Putalisadak, Kathmandu")}
            <br />
            {t("Sunday to Friday, 10 am – 6 pm")}
          </p>
        </div>
        <div className="text-sm">
          <p className="mb-2 text-white">{t("Talk to us")}</p>
          <a href={`tel:${OFFICE.phoneTel}`} className="block hover:text-white">{OFFICE.phone}</a>
          <a href={`mailto:${OFFICE.email}`} className="block hover:text-white">
            {OFFICE.email}
          </a>
          <Link to="/privacy" className="mt-3 block hover:text-white">
            {t("Privacy")}
          </Link>
          <Link to="/staff/login" className="mt-1 block text-white/50 hover:text-white">
            Staff sign in
          </Link>
        </div>
        <div className="text-sm leading-relaxed">
          <p className="mb-2 text-white">{t("A note on our figures")}</p>
          <p>
            {t("Tuition and scholarship deadlines change. Every listing shows when we last checked it, and we ask you to confirm with the university before you pay anything.")}
          </p>
        </div>
      </div>
      {__SAMPLE_NOTICE__ && (
        <div className="border-t border-white/10 py-4 text-center text-xs text-white/50">
          {t("Demonstration site. All universities, fees and students shown here are sample data.")}
        </div>
      )}
    </footer>
  );
}

export default function App() {
  const isStaff = useLocation().pathname.startsWith("/staff");

  return (
    <div className="flex min-h-screen flex-col">
      {isStaff ? <StaffHeader /> : <PublicHeader />}
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/apply" element={<Apply />} />
          <Route path="/study/:slug" element={<CountryPage />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/staff/login" element={<StaffLogin />} />
          <Route path="/staff" element={<RequireLogin><StaffDashboard /></RequireLogin>} />
          <Route path="/staff/new" element={<RequireLogin><AddStudent /></RequireLogin>} />
          <Route path="/staff/leads/:id" element={<RequireLogin><LeadDetail /></RequireLogin>} />
          <Route path="/staff/team" element={<RequireLogin><Team /></RequireLogin>} />
          <Route path="/staff/reports" element={<RequireLogin><Reports /></RequireLogin>} />
          <Route path="/staff/password" element={<RequireLogin><ChangePassword /></RequireLogin>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      {!isStaff && <PublicFooter />}
    </div>
  );
}