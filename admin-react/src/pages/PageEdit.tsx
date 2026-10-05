import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card'

export default function PageEdit() {
  return (
    <div className="PageEdit-page">
      <div className="page-header">
        <h1>PageEdit</h1>
        <p className="page-subtitle">Страница в разработке</p>
      </div>
      <Card>
        <CardContent>
          <p className="text-muted">Эта страница будет реализована в рамках миграции на React SPA.</p>
        </CardContent>
      </Card>
    </div>
  )
}
