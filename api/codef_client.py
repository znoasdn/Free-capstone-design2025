"""
CODEF API 클라이언트
운전면허증 진위확인 API 연동

API 문서: https://developer.codef.io/products/public/each/ef/driver-license
"""
import requests
import json
import base64
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class CodefClient:
    """CODEF API 클라이언트"""
    
    # API 엔드포인트
    ENDPOINTS = {
        "development": "https://development.codef.io",
        "production": "https://api.codef.io"
    }
    
    def __init__(
        self, 
        client_id: str, 
        client_secret: str, 
        is_production: bool = False
    ):
        """
        CODEF API 클라이언트 초기화
        
        Args:
            client_id: CODEF 클라이언트 ID
            client_secret: CODEF 클라이언트 시크릿
            is_production: True면 운영환경, False면 개발환경
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_production = is_production
        
        # 환경에 따른 Base URL 설정
        env = "production" if is_production else "development"
        self.base_url = self.ENDPOINTS[env]
        
        # 토큰 캐시
        self._token: Optional[str] = None
        self._token_type: str = "Bearer"
    
    def _get_auth_header(self) -> str:
        """Basic 인증 헤더 생성"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    def _request_token(self) -> str:
        """
        OAuth 액세스 토큰 발급
        
        Returns:
            액세스 토큰 문자열
            
        Raises:
            Exception: 토큰 발급 실패 시
        """
        url = f"{self.base_url}/oauth/token"
        
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self._token = result.get("access_token")
                self._token_type = result.get("token_type", "Bearer")
                logger.info("CODEF 토큰 발급 성공")
                return self._token
            else:
                error_msg = f"토큰 발급 실패: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"토큰 요청 중 네트워크 오류: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_token(self) -> str:
        """
        액세스 토큰 반환 (캐시된 토큰 또는 새로 발급)
        
        Returns:
            액세스 토큰 문자열
        """
        if self._token:
            return self._token
        return self._request_token()
    
    def _make_request(
        self, 
        endpoint: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        API 요청 실행
        
        Args:
            endpoint: API 엔드포인트 경로
            payload: 요청 바디
            
        Returns:
            API 응답 딕셔너리
        """
        token = self.get_token()
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"{self._token_type} {token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error("API 요청 타임아웃")
            return {
                "result": {
                    "code": "TIMEOUT",
                    "message": "API 요청 시간 초과"
                }
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 오류: {str(e)}")
            return {
                "result": {
                    "code": "NETWORK_ERROR",
                    "message": f"네트워크 오류: {str(e)}"
                }
            }
        except json.JSONDecodeError:
            logger.error("API 응답 파싱 오류")
            return {
                "result": {
                    "code": "PARSE_ERROR",
                    "message": "API 응답 파싱 실패"
                }
            }
    
    def verify_driver_license(
        self,
        license_number: str,
        name: str,
        birth_date: str,
        serial_number: str
    ) -> Dict[str, Any]:
        """
        운전면허증 진위확인
        
        Args:
            license_number: 운전면허번호 (12자리, 하이픈 포함 가능)
            name: 성명
            birth_date: 생년월일 (YYYYMMDD 형식)
            serial_number: 암호일련번호 (면허증 우측 하단 6자리)
            
        Returns:
            {
                "success": bool,      # API 호출 성공 여부
                "valid": bool,        # 진위확인 결과 (True: 정상)
                "status": str,        # 상태 ("확인", "불일치", "오류")
                "message": str,       # 결과 메시지
                "details": dict,      # 상세 정보
                "raw_response": dict  # 원본 API 응답
            }
        """
        # 운전면허번호 정제 (하이픈, 공백 제거)
        license_clean = license_number.replace("-", "").replace(" ", "")
        
        # 생년월일 정제
        birth_clean = birth_date.replace("-", "").replace(".", "").replace(" ", "")
        
        # API 요청 페이로드
        payload = {
            "organization": "0002",      # 경찰청
            "loginType": "5",            # 간편인증
            "identity": birth_clean,     # 생년월일 (YYYYMMDD)
            "userName": name,            # 성명
            "licenseNo": license_clean,  # 운전면허번호
            "serialNo": serial_number    # 암호일련번호
        }
        
        logger.info(f"운전면허 진위확인 요청: {license_clean[:4]}****{license_clean[-2:]}")
        
        # API 호출
        response = self._make_request(
            "/v1/kr/public/ef/driver-license/status",
            payload
        )
        
        # 응답 파싱
        return self._parse_driver_license_response(response)
    
    def _parse_driver_license_response(
        self, 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        운전면허 진위확인 응답 파싱
        
        Args:
            response: API 원본 응답
            
        Returns:
            파싱된 결과 딕셔너리
        """
        result_code = response.get("result", {}).get("code", "")
        result_message = response.get("result", {}).get("message", "")
        
        # 성공 응답 (CF-00000)
        if result_code == "CF-00000":
            data = response.get("data", {})
            
            # 진위확인 결과
            # resAuthenticity: "1" = 정상, "2" = 불일치
            authenticity = data.get("resAuthenticity", "")
            authenticity_desc = data.get("resAuthenticityDesc", "")
            
            if authenticity == "1":
                return {
                    "success": True,
                    "valid": True,
                    "status": "확인",
                    "message": "운전면허증 진위확인 완료 (정상)",
                    "details": {
                        "authenticity": authenticity,
                        "description": authenticity_desc,
                        "license_type": data.get("resLicenseType", ""),
                        "issue_date": data.get("resIssueDate", ""),
                        "expiry_date": data.get("resExpiryDate", "")
                    },
                    "raw_response": response
                }
            else:
                return {
                    "success": True,
                    "valid": False,
                    "status": "불일치",
                    "message": f"운전면허증 정보 불일치: {authenticity_desc}",
                    "details": {
                        "authenticity": authenticity,
                        "description": authenticity_desc
                    },
                    "raw_response": response
                }
        
        # 에러 응답
        else:
            return {
                "success": False,
                "valid": False,
                "status": "오류",
                "message": f"API 오류 ({result_code}): {result_message}",
                "details": {
                    "error_code": result_code,
                    "error_message": result_message
                },
                "raw_response": response
            }
    
    def verify_identity_card(
        self,
        card_type: str,
        identity_number: str,
        name: str,
        issue_date: str
    ) -> Dict[str, Any]:
        """
        신분증 진위확인 (주민등록증, 외국인등록증 등)
        
        Args:
            card_type: 신분증 종류 ("resident": 주민등록증, "foreigner": 외국인등록증)
            identity_number: 주민등록번호/외국인등록번호 (13자리)
            name: 성명
            issue_date: 발급일자 (YYYYMMDD)
            
        Returns:
            진위확인 결과 딕셔너리
        """
        # 번호 정제
        id_clean = identity_number.replace("-", "").replace(" ", "")
        issue_clean = issue_date.replace("-", "").replace(".", "")
        
        payload = {
            "organization": "0002",
            "loginType": "5",
            "identity": id_clean,
            "userName": name,
            "issueDate": issue_clean
        }
        
        # 신분증 종류에 따른 엔드포인트
        if card_type == "foreigner":
            endpoint = "/v1/kr/public/mw/foreigners-card/status"
        else:
            endpoint = "/v1/kr/public/mw/identity-card/check-status"
        
        logger.info(f"신분증 진위확인 요청: {card_type}")
        
        response = self._make_request(endpoint, payload)
        
        return self._parse_identity_card_response(response, card_type)
    
    def _parse_identity_card_response(
        self, 
        response: Dict[str, Any],
        card_type: str
    ) -> Dict[str, Any]:
        """신분증 진위확인 응답 파싱"""
        result_code = response.get("result", {}).get("code", "")
        result_message = response.get("result", {}).get("message", "")
        
        card_name = "주민등록증" if card_type == "resident" else "외국인등록증"
        
        if result_code == "CF-00000":
            data = response.get("data", {})
            authenticity = data.get("resAuthenticity", "")
            
            if authenticity == "1":
                return {
                    "success": True,
                    "valid": True,
                    "status": "확인",
                    "message": f"{card_name} 진위확인 완료 (정상)",
                    "details": data,
                    "raw_response": response
                }
            else:
                return {
                    "success": True,
                    "valid": False,
                    "status": "불일치",
                    "message": f"{card_name} 정보 불일치",
                    "details": data,
                    "raw_response": response
                }
        else:
            return {
                "success": False,
                "valid": False,
                "status": "오류",
                "message": f"API 오류: {result_message}",
                "details": {"error_code": result_code},
                "raw_response": response
            }


class CodefApiError(Exception):
    """CODEF API 관련 예외"""
    
    def __init__(self, code: str, message: str, response: dict = None):
        self.code = code
        self.message = message
        self.response = response or {}
        super().__init__(f"[{code}] {message}")
