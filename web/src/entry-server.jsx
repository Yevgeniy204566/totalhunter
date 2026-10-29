// Серверная отрисовка для пререндера (prerender.mjs): отдаёт HTML страницы со всем текстом, заголовками и ссылками,
// чтобы поисковик видел содержимое без выполнения скриптов. В браузере тот же маршрут гидрируется из main.jsx.
import { renderToString } from 'react-dom/server'
import { StaticRouter } from 'react-router-dom'
import App from './App.jsx'
import { LangProvider } from './lang.js'

export function render(url) {
  return renderToString(
    <StaticRouter location={url}>
      <LangProvider>
        <App />
      </LangProvider>
    </StaticRouter>
  )
}
