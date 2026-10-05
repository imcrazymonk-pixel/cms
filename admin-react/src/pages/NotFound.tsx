import { Button } from '../components/ui/button'
import { SearchX } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="not-found-page">
      <div className="not-found-content">
        <div className="not-found-code">404</div>
        <h1>Страница не найдена</h1>
        <p>Запрашиваемая страница не существует или была удалена.</p>
        <Button variant="primary" onClick={() => window.location.href = '/admin/'}>
          На дашборд
        </Button>
      </div>
    </div>
  )
}