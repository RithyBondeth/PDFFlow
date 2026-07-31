import { apiProxyTarget } from '../utils/apiProxy'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const requestUrl = getRequestURL(event)
  const target = apiProxyTarget(
    String(config.apiInternal),
    `${requestUrl.pathname}${requestUrl.search}`,
  )

  return proxyRequest(event, target)
})
