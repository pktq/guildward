import { Footer } from "@/components/site/Footer";
import { Header } from "@/components/site/Header";
import "@/components/site/site.css";

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="gw-site">
      <a href="#main" className="gw-skip">
        Skip to content
      </a>
      <Header />
      <main id="main">{children}</main>
      <Footer />
    </div>
  );
}
