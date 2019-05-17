from __future__ import absolute_import, print_function, unicode_literals

from aiohttp import web
from aiohttp.formdata import FormData
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from wolframclient.evaluation import WolframEvaluatorPool
from wolframclient.language import wl
from wolframclient.utils import six
from wolframclient.utils.functional import first
from wolframwebengine.web import aiohttp_wl_view


class MyAppTestCase(AioHTTPTestCase):
    async def get_application(self):

        self.session = WolframEvaluatorPool(poolsize=4)
        routes = web.RouteTableDef()

        @routes.get('/')
        async def hello(request):
            return web.Response(text="Hello from aiohttp")

        @routes.get('/form')
        @routes.post('/form')
        @aiohttp_wl_view(self.session)
        async def form_view(request):
            return wl.FormFunction({"x": "String"}, wl.Identity, "JSON")

        @routes.get('/api')
        @routes.post('/api')
        @aiohttp_wl_view(self.session)
        async def api_view(request):
            return wl.APIFunction({"x": "String"}, wl.Identity, "JSON")

        app = web.Application()
        app.add_routes(routes)

        return app

    @unittest_run_loop
    async def test_aiohhtp(self):

        resp = await self.client.request("GET", "/")

        self.assertEqual(resp.status, 200)
        self.assertEqual(await resp.text(), "Hello from aiohttp")

        resp = await self.client.request("GET", "/api")

        self.assertEqual(resp.status, 400)
        self.assertEqual((await resp.json())["Success"], False)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')

        resp = await self.client.request("GET", "/api?x=a")

        self.assertEqual(resp.status, 200)
        self.assertEqual((await resp.json())["x"], "a")
        self.assertEqual(resp.headers['Content-Type'], 'application/json')

        resp = await self.client.request("GET", "/form")

        self.assertEqual(resp.status, 200)
        self.assertEqual(
            first(resp.headers['Content-Type'].split(';')), 'text/html')

        resp = await self.client.request("POST", "/form", data={'x': "foobar"})

        self.assertEqual(resp.status, 200)
        self.assertEqual((await resp.json())["x"], "foobar")
        self.assertEqual(resp.headers['Content-Type'], 'application/json')

        stream = six.BytesIO()
        stream.write(b'foobar')
        stream.seek(0)

        data = FormData()
        data.add_field('x', stream, filename='pixeltez.txt')

        resp = await self.client.request("POST", "/form", data=data)

        self.assertEqual(resp.status, 200)
        self.assertEqual((await resp.json())["x"], "foobar")
        self.assertEqual(resp.headers['Content-Type'], 'application/json')

    def tearDown(self):
        if self.session.started:
            self.loop.run_until_complete(self.session.stop())
        super().tearDown()
