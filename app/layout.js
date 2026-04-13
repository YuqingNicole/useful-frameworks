import './globals.css'

export const metadata = {
  title: 'Useful Frameworks',
  description: '好用的框架和工具集合',
}

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}
