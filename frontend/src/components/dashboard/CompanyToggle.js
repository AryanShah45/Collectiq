import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { COMPANY } from "@/lib/calc";

export default function CompanyToggle({ value, onChange }) {
  return (
    <Tabs value={value} onValueChange={onChange} data-testid="company-toggle">
      <TabsList className="bg-secondary">
        <TabsTrigger value={COMPANY.ALL} data-testid="company-all">All</TabsTrigger>
        <TabsTrigger value={COMPANY.MBS} data-testid="company-mbs">MBS</TabsTrigger>
        <TabsTrigger value={COMPANY.MCORP} data-testid="company-mcorp">MCORP</TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
