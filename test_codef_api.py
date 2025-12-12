"""
CODEF API 클라이언트 테스트
- API 연결 테스트
- 운전면허 진위확인 테스트

주의: 실제 API 테스트는 CODEF 계정이 필요합니다.
      이 테스트는 주로 코드 구조와 로직을 검증합니다.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json


class TestCodefClient(unittest.TestCase):
    """CodefClient 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        from api.codef_client import CodefClient
        
        # 테스트용 클라이언트 (개발 환경)
        self.client = CodefClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            is_production=False
        )
    
    def test_init_development(self):
        """개발 환경 초기화 테스트"""
        self.assertEqual(
            self.client.base_url, 
            "https://development.codef.io"
        )
        self.assertFalse(self.client.is_production)
    
    def test_init_production(self):
        """운영 환경 초기화 테스트"""
        from api.codef_client import CodefClient
        
        client = CodefClient(
            client_id="test",
            client_secret="test",
            is_production=True
        )
        self.assertEqual(
            client.base_url,
            "https://api.codef.io"
        )
        self.assertTrue(client.is_production)
    
    def test_auth_header(self):
        """인증 헤더 생성 테스트"""
        import base64
        
        auth_header = self.client._get_auth_header()
        
        # Basic 인증 형식 확인
        self.assertTrue(auth_header.startswith("Basic "))
        
        # 디코딩 확인
        encoded_part = auth_header.replace("Basic ", "")
        decoded = base64.b64decode(encoded_part).decode()
        self.assertEqual(decoded, "test_client_id:test_client_secret")
    
    @patch('requests.post')
    def test_request_token_success(self, mock_post):
        """토큰 발급 성공 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "token_type": "Bearer"
        }
        mock_post.return_value = mock_response
        
        # 토큰 발급
        token = self.client._request_token()
        
        # 검증
        self.assertEqual(token, "test_access_token")
        self.assertEqual(self.client._token, "test_access_token")
        self.assertEqual(self.client._token_type, "Bearer")
    
    @patch('requests.post')
    def test_request_token_failure(self, mock_post):
        """토큰 발급 실패 테스트"""
        # Mock 응답 설정 (실패)
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        # 예외 발생 확인
        with self.assertRaises(Exception) as context:
            self.client._request_token()
        
        self.assertIn("토큰 발급 실패", str(context.exception))
    
    @patch('requests.post')
    def test_verify_driver_license_success(self, mock_post):
        """운전면허 진위확인 성공 테스트"""
        # 토큰 응답
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer"
        }
        
        # API 응답 (성공)
        api_response = Mock()
        api_response.json.return_value = {
            "result": {
                "code": "CF-00000",
                "message": "성공"
            },
            "data": {
                "resAuthenticity": "1",
                "resAuthenticityDesc": "정상",
                "resLicenseType": "1종보통",
                "resIssueDate": "20200101",
                "resExpiryDate": "20300101"
            }
        }
        
        # 두 번의 POST 호출 (토큰, API)
        mock_post.side_effect = [token_response, api_response]
        
        # 진위확인 호출
        result = self.client.verify_driver_license(
            license_number="11-23-123456-78",
            name="홍길동",
            birth_date="19900101",
            serial_number="ABC123"
        )
        
        # 검증
        self.assertTrue(result["success"])
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "확인")
        self.assertIn("정상", result["message"])
    
    @patch('requests.post')
    def test_verify_driver_license_mismatch(self, mock_post):
        """운전면허 진위확인 불일치 테스트"""
        # 토큰 응답
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer"
        }
        
        # API 응답 (불일치)
        api_response = Mock()
        api_response.json.return_value = {
            "result": {
                "code": "CF-00000",
                "message": "성공"
            },
            "data": {
                "resAuthenticity": "2",
                "resAuthenticityDesc": "정보 불일치"
            }
        }
        
        mock_post.side_effect = [token_response, api_response]
        
        result = self.client.verify_driver_license(
            license_number="11-23-123456-78",
            name="홍길동",
            birth_date="19900101",
            serial_number="ABC123"
        )
        
        # 검증
        self.assertTrue(result["success"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "불일치")
    
    @patch('requests.post')
    def test_verify_driver_license_api_error(self, mock_post):
        """운전면허 진위확인 API 오류 테스트"""
        # 토큰 응답
        token_response = Mock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer"
        }
        
        # API 응답 (오류)
        api_response = Mock()
        api_response.json.return_value = {
            "result": {
                "code": "CF-99999",
                "message": "시스템 오류"
            }
        }
        
        mock_post.side_effect = [token_response, api_response]
        
        result = self.client.verify_driver_license(
            license_number="11-23-123456-78",
            name="홍길동",
            birth_date="19900101",
            serial_number="ABC123"
        )
        
        # 검증
        self.assertFalse(result["success"])
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "오류")
    
    def test_license_number_cleaning(self):
        """운전면허번호 정제 테스트"""
        # 하이픈 포함
        license_with_hyphen = "11-23-123456-78"
        clean = license_with_hyphen.replace("-", "").replace(" ", "")
        self.assertEqual(clean, "112312345678")
        
        # 공백 포함
        license_with_space = "11 23 123456 78"
        clean = license_with_space.replace("-", "").replace(" ", "")
        self.assertEqual(clean, "112312345678")


class TestDriverLicenseValidatorWithApi(unittest.TestCase):
    """DriverLicenseValidator API 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        from validators.driver_license_validator import DriverLicenseValidator
        self.validator = DriverLicenseValidator()
    
    @patch('core.config.Config')
    @patch('api.codef_client.CodefClient')
    def test_validate_with_api_not_configured(self, mock_client_class, mock_config_class):
        """API 미설정 시 테스트"""
        # Config mock 설정
        mock_config = Mock()
        mock_config.is_codef_configured.return_value = False
        mock_config_class.return_value = mock_config
        
        # API 검증 호출
        success, result_type, details = self.validator.validate_with_api(
            "112312345678",
            "홍길동",
            "19900101",
            "ABC123"
        )
        
        # 검증
        self.assertFalse(success)
        self.assertIn("설정되지 않았습니다", result_type)


class TestConfigCodefSettings(unittest.TestCase):
    """Config CODEF 설정 테스트"""
    
    def test_codef_settings_exist(self):
        """CODEF 설정 메서드 존재 확인"""
        from core.config import Config
        
        config = Config()
        
        # 메서드 존재 확인
        self.assertTrue(hasattr(config, 'get_codef_enabled'))
        self.assertTrue(hasattr(config, 'set_codef_enabled'))
        self.assertTrue(hasattr(config, 'get_codef_client_id'))
        self.assertTrue(hasattr(config, 'set_codef_client_id'))
        self.assertTrue(hasattr(config, 'get_codef_client_secret'))
        self.assertTrue(hasattr(config, 'set_codef_client_secret'))
        self.assertTrue(hasattr(config, 'get_codef_production'))
        self.assertTrue(hasattr(config, 'set_codef_production'))
        self.assertTrue(hasattr(config, 'is_codef_configured'))
    
    def test_is_codef_configured_false(self):
        """CODEF 미설정 상태 테스트"""
        from core.config import Config
        
        config = Config()
        
        # 기본값은 False
        # (실제 설정이 없는 경우)
        result = config.is_codef_configured()
        # 설정이 없으면 False
        self.assertFalse(result)


class TestConstantsApiTypes(unittest.TestCase):
    """Constants에 API 타입 추가 확인"""
    
    def test_severity_weights_api_types(self):
        """SEVERITY_WEIGHTS에 API 타입 존재 확인"""
        from utils.constants import SEVERITY_WEIGHTS
        
        self.assertIn("운전면허번호(API확인)", SEVERITY_WEIGHTS)
        self.assertIn("운전면허번호(API불일치)", SEVERITY_WEIGHTS)
        
        # API 확인은 높은 가중치 (확정)
        self.assertGreater(
            SEVERITY_WEIGHTS["운전면허번호(API확인)"],
            SEVERITY_WEIGHTS["운전면허번호"]
        )
        
        # API 불일치는 낮은 가중치
        self.assertLess(
            SEVERITY_WEIGHTS["운전면허번호(API불일치)"],
            SEVERITY_WEIGHTS["운전면허번호(의심)"]
        )
    
    def test_highlight_colors_api_types(self):
        """HIGHLIGHT_COLORS에 API 타입 존재 확인"""
        from utils.constants import HIGHLIGHT_COLORS
        
        self.assertIn("운전면허번호(API확인)", HIGHLIGHT_COLORS)
        self.assertIn("운전면허번호(API불일치)", HIGHLIGHT_COLORS)
    
    def test_info_legal_category_api_types(self):
        """INFO_LEGAL_CATEGORY에 API 타입 존재 확인"""
        from utils.constants import INFO_LEGAL_CATEGORY
        
        self.assertIn("운전면허번호(API확인)", INFO_LEGAL_CATEGORY)
        self.assertIn("운전면허번호(API불일치)", INFO_LEGAL_CATEGORY)
        
        # 모두 고유식별정보
        self.assertEqual(
            INFO_LEGAL_CATEGORY["운전면허번호(API확인)"],
            "고유식별정보"
        )


if __name__ == "__main__":
    print("=" * 60)
    print("CODEF API 테스트")
    print("=" * 60)
    
    # 테스트 실행
    unittest.main(verbosity=2)
