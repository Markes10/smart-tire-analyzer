import importlib
m_config = importlib.import_module('backend.app.config')
print('GEMINI_KEYS', m_config.Settings.get_gemini_keys())
import backend.app.services.key_manager as km
rot = km.get_rotator('gemini', m_config.Settings.get_gemini_keys())
print('ROTATOR_HAS', rot.has_keys(), 'CURRENT', rot.get_key())
import importlib as il
gs = il.import_module('backend.app.services.gemini_service')
ms = il.import_module('backend.app.services.maps_service')
ws = il.import_module('backend.app.services.weather_service')
print('GeminiService enabled:', gs.GeminiService().enabled)
print('MapsService enabled:', ms.MapsService().enabled)
print('WeatherService enabled:', ws.WeatherService().enabled)
