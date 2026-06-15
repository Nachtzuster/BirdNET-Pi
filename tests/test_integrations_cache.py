import os
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

from backend.app.routers import integrations


class DummySettings:
    def __init__(self, base_path: str, image_provider: str = 'wikipedia'):
        self._base_path = base_path
        self._image_provider = image_provider

    @property
    def base_path(self) -> str:
        return self._base_path

    @property
    def image_provider(self) -> str:
        return self._image_provider

    @property
    def flickr_api_key(self) -> str:
        return ''


class TestIntegrationsCache(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        integrations._wikimedia_request_lock = None
        integrations._wikimedia_lock_loop_id = None
        integrations._wikimedia_next_request_at = 0.0
        integrations._wikimedia_cooldown_until = 0.0

    def test_negative_cache_fresh(self):
        cached_meta = {
            'has_image': 0,
            'last_checked_epoch': int(time.time()),
        }
        self.assertTrue(integrations.is_negative_cache_fresh(cached_meta))

    def test_build_local_asset_url(self):
        self.assertEqual(
            integrations.build_local_asset_url('wikipedia', 'Corvus corax'),
            '/api/image-asset/wikipedia/Corvus corax',
        )

    def test_rewrite_wikimedia_thumbnail_url(self):
        original = (
            'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/'
            'Pine_warbler_%2890070%29.jpg/1024px-Pine_warbler_%2890070%29.jpg'
        )
        rewritten = integrations.rewrite_wikimedia_thumbnail_url(original)
        self.assertIn('/640px-', rewritten)
        self.assertNotIn('/1024px-', rewritten)

    async def test_negative_cache_skips_wikipedia_fetch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'scripts'), exist_ok=True)
            settings = DummySettings(base_path=tmpdir)
            integrations.cache_fetch_meta(
                sci_name='Corvus corax',
                has_image=False,
                provider='wikipedia',
                settings=settings,
            )

            with patch(
                'backend.app.routers.integrations.fetch_wikipedia_image',
                new=AsyncMock(return_value=(None, True)),
            ) as mock_fetch:
                image = await integrations.get_bird_image(
                    sci_name='Corvus corax',
                    force_refresh=False,
                    settings=settings,
                )

            self.assertIsNone(image)
            mock_fetch.assert_not_called()

    async def test_local_asset_is_preferred_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'scripts'), exist_ok=True)
            settings = DummySettings(base_path=tmpdir)
            integrations.cache_image(
                sci_name='Corvus corax',
                image_data={'url': 'https://example.com/raven.jpg', 'title': 'Raven'},
                provider='wikipedia',
                settings=settings,
            )
            local_relative_path = os.path.join('scripts', 'image-cache', 'wikipedia', 'Corvus_corax.jpg')
            local_absolute_path = os.path.join(tmpdir, local_relative_path)
            os.makedirs(os.path.dirname(local_absolute_path), exist_ok=True)
            with open(local_absolute_path, 'wb') as image_file:
                image_file.write(b'test')
            integrations.cache_fetch_meta(
                sci_name='Corvus corax',
                has_image=True,
                provider='wikipedia',
                settings=settings,
                local_path=local_relative_path,
            )

            image = await integrations.get_bird_image(
                sci_name='Corvus corax',
                force_refresh=False,
                settings=settings,
            )

            self.assertIsNotNone(image)
            self.assertEqual(image.url, '/api/image-asset/wikipedia/Corvus corax')

    async def test_cached_wikipedia_image_uses_local_endpoint_without_local_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'scripts'), exist_ok=True)
            settings = DummySettings(base_path=tmpdir)
            integrations.cache_image(
                sci_name='Sitta pusilla',
                image_data={'url': 'https://upload.wikimedia.org/example.jpg', 'title': 'Brown-headed Nuthatch'},
                provider='wikipedia',
                settings=settings,
            )

            image = await integrations.get_bird_image(
                sci_name='Sitta pusilla',
                force_refresh=False,
                settings=settings,
            )

            self.assertIsNotNone(image)
            self.assertEqual(image.url, '/api/image-asset/wikipedia/Sitta pusilla')

    async def test_asset_endpoint_refetches_summary_when_cached_url_is_not_remote(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'scripts'), exist_ok=True)
            settings = DummySettings(base_path=tmpdir)
            integrations.cache_image(
                sci_name='Sitta pusilla',
                image_data={'url': '/api/image-asset/wikipedia/Sitta pusilla', 'title': 'Brown-headed Nuthatch'},
                provider='wikipedia',
                settings=settings,
            )

            with patch(
                'backend.app.routers.integrations.fetch_wikipedia_image',
                new=AsyncMock(return_value=(
                    integrations.BirdImage(
                        url='https://upload.wikimedia.org/example.jpg',
                        title='Brown-headed Nuthatch',
                        source='wikipedia',
                    ),
                    True,
                )),
            ) as mock_fetch:
                with patch(
                    'backend.app.routers.integrations.cache_remote_image_asset',
                    new=AsyncMock(return_value=os.path.join('scripts', 'image-cache', 'wikipedia', 'Sitta_pusilla.jpg')),
                ):
                    local_path = await integrations.ensure_local_image_asset(
                        sci_name='Sitta pusilla',
                        provider='wikipedia',
                        settings=settings,
                    )

            self.assertEqual(local_path, os.path.join('scripts', 'image-cache', 'wikipedia', 'Sitta_pusilla.jpg'))
            mock_fetch.assert_called_once()

    async def test_cached_asset_response_sets_browser_cache_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, 'scripts'), exist_ok=True)
            settings = DummySettings(base_path=tmpdir)
            local_relative_path = os.path.join('scripts', 'image-cache', 'wikipedia', 'Corvus_corax.jpg')
            local_absolute_path = os.path.join(tmpdir, local_relative_path)
            os.makedirs(os.path.dirname(local_absolute_path), exist_ok=True)
            with open(local_absolute_path, 'wb') as image_file:
                image_file.write(b'test')
            integrations.cache_fetch_meta(
                sci_name='Corvus corax',
                has_image=True,
                provider='wikipedia',
                settings=settings,
                local_path=local_relative_path,
            )

            response = await integrations.get_cached_image_asset(
                provider='wikipedia',
                sci_name='Corvus corax',
                settings=settings,
            )

            self.assertEqual(
                response.headers.get('cache-control'),
                'public, max-age=604800, stale-while-revalidate=86400',
            )


if __name__ == '__main__':
    unittest.main()
