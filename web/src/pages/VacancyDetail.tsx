import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useVacancy, useVacancyReport } from "@/api/hooks";
import { decisionLabel, decisionVariant } from "@/lib/format";
import { CallsTable } from "@/components/CallsTable";
import { CandidatesUpload } from "@/components/CandidatesUpload";

export function VacancyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id ? Number(params.id) : null;

  const { data: vacancy, isLoading } = useVacancy(id);
  const { data: report } = useVacancyReport(id);

  if (isLoading || !vacancy) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link
          to="/vacancies"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />К списку вакансий
        </Link>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{vacancy.title}</h1>
            <p className="text-sm text-muted-foreground">
              <span className="font-mono">{vacancy.scenario_name}</span> · порог {vacancy.pass_score}
            </p>
          </div>
          <Badge variant={vacancy.active ? "success" : "secondary"}>
            {vacancy.active ? "Активна" : "Архив"}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <ReportCard label="Кандидатов" value={report?.candidates_total} />
        <ReportCard label="Звонков" value={report?.calls_total} />
        <ReportCard label="С оценкой" value={report?.calls_with_score} />
        <ReportCard
          label="Средний score"
          value={report?.avg_score != null ? report.avg_score.toFixed(2) : "—"}
        />
      </div>

      {report && Object.keys(report.by_decision).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Решения по звонкам</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {Object.entries(report.by_decision).map(([d, count]) => (
              <Badge key={d} variant={decisionVariant(d)}>
                {decisionLabel(d)} · {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="calls">
        <TabsList>
          <TabsTrigger value="calls">Звонки</TabsTrigger>
          <TabsTrigger value="upload">Загрузить кандидатов</TabsTrigger>
        </TabsList>
        <TabsContent value="calls">
          <CallsTable vacancyId={vacancy.id} />
        </TabsContent>
        <TabsContent value="upload">
          <CandidatesUpload vacancyId={vacancy.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ReportCard({ label, value }: { label: string; value: number | string | undefined }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">
          {value ?? <span className="text-muted-foreground">—</span>}
        </div>
      </CardContent>
    </Card>
  );
}
