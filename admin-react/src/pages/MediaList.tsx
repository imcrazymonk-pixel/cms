import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card'

export default function MediaList() {
  return (
    <div className="MediaList-page">
      <div className="page-header">
        <h1>MediaList</h1>
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
