export class ErrorHandler {
  static getUserFriendlyMessage(error) {
    if (typeof error === 'string' && !ErrorHandler.isTechnicalError(error)) {
      return error;
    }

    if (error && typeof error === 'object') {
      const status = error.status || error.code;
      const message = error.message || error.error;

      if (message && !ErrorHandler.isTechnicalError(message)) {
        return message;
      }

      return ErrorHandler.getStatusMessage(status);
    }

    return 'Произошла неожиданная ошибка. Попробуйте еще раз.';
  }

  static isTechnicalError(message) {
    if (typeof message !== 'string') return false;
    
    const technicalKeywords = [
      'gRPC',
      'localhost',
      'Connection refused',
      'UNKNOWN',
      'StatusCode',
      'AioRpcError',
      'failed to connect',
      'ipv6',
      'ipv4',
      'grpc_status',
      'grpc_message',
      'debug_error_string',
      'Internal Server Error',
      'Bad Gateway',
      'Service Unavailable'
    ];

    return technicalKeywords.some(keyword => 
      message.toLowerCase().includes(keyword.toLowerCase())
    );
  }

  static getStatusMessage(status) {
    switch (status) {
      case 0:
        return 'Ошибка сети. Проверьте подключение к серверу инжестора.';
      case 400:
        return 'Неверные данные. Проверьте введенную информацию.';
      case 401:
        return 'Доступ запрещен. Проверьте права доступа.';
      case 403:
        return 'Доступ запрещен. Проверьте права доступа.';
      case 404:
        return 'Запрашиваемый ресурс не найден.';
      case 409:
        return 'Конфликт данных. Попробуйте еще раз.';
      case 422:
        return 'Данные не прошли валидацию. Проверьте введенную информацию.';
      case 429:
        return 'Слишком много запросов. Подождите немного и попробуйте снова.';
      case 500:
        return 'Сервис инжестора временно недоступен. Попробуйте позже.';
      case 502:
        return 'Сервис инжестора временно недоступен. Попробуйте позже.';
      case 503:
        return 'Сервис перегружен. Попробуйте через несколько минут.';
      case 504:
        return 'Превышено время ожидания ответа. Попробуйте еще раз.';
      default:
        return 'Произошла ошибка. Попробуйте еще раз.';
    }
  }

  static logError(error, context = '') {
    if (ErrorHandler.isTechnicalError(error.message || error)) {
      console.error(`[${context}] Technical error:`, error);
    } else {
      console.warn(`[${context}] User error:`, error);
    }
  }
}

export const getUserFriendlyError = ErrorHandler.getUserFriendlyMessage;
export const logError = ErrorHandler.logError;