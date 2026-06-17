import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import TrustStrip from "@/components/TrustStrip";
import FlagshipCards from "@/components/FlagshipCards";
import FeaturePrompts from "@/components/FeaturePrompts";
import ToolExplorer from "@/components/ToolExplorer";
import ComparisonTable from "@/components/ComparisonTable";
import PricingSection from "@/components/PricingSection";
import HowItWorks from "@/components/HowItWorks";
import Quickstart from "@/components/Quickstart";
import Footer from "@/components/Footer";
import BackgroundCarousel from "@/components/BackgroundCarousel";

export default function Home() {
  return (
    <main className="min-h-screen relative selection:bg-action-blue/30 selection:text-black">
      <BackgroundCarousel />
      <Navbar />
      
      <div className="pt-16">
        <Hero />
        <TrustStrip />
        <FlagshipCards />
        <FeaturePrompts />
        <ToolExplorer />
        <ComparisonTable />
        <PricingSection />
        <HowItWorks />
        <Quickstart />
      </div>

      <Footer />
    </main>
  );
}
