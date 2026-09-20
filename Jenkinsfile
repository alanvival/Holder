pipeline {
    agent any

    stages {
        stage('Localizar Python') {
            steps {
                script {
                    def python = bat(
                        script: '''
                            @echo off
                            where python >nul 2>&1
                            if %ERRORLEVEL% EQU 0 (
                                echo python
                                exit /b 0
                            )

                            if exist "%LocalAppData%\\Programs\\Python\\Python313\\python.exe" (
                                echo %LocalAppData%\\Programs\\Python\\Python313\\python.exe
                                exit /b 0
                            )

                            if exist "%LocalAppData%\\Python\\bin\\python.exe" (
                                echo %LocalAppData%\\Python\\bin\\python.exe
                                exit /b 0
                            )

                            if exist "C:\\Python313\\python.exe" (
                                echo C:\\Python313\\python.exe
                                exit /b 0
                            )

                            echo Python nao encontrado
                            exit /b 1
                        ''',
                        returnStdout: true
                    ).trim()

                    env.PYTHON = python.split('\r\n')[-1].trim()

                    echo "Python encontrado em: ${env.PYTHON}"
                }
            }
        }

        stage('Verificar Python') {
            steps {
                bat '''
                    "%PYTHON%" --version
                    "%PYTHON%" -m pip --version
                '''
            }
        }

        stage('Instalar dependências') {
            steps {
                bat '''
                    "%PYTHON%" -m pip install -r requirements.txt
                '''
            }
        }

        stage('Atualizar banco') {
            steps {
                bat '''
                    "%PYTHON%" -m holder.infra.etl.ingestao
                '''
            }
        }

        stage('Treinar modelo') {
            steps {
                bat '''
                    "%PYTHON%" -m holder.aplicacao.treino
                '''
            }
        }

        stage('Gerar dados InovaApps') {
            steps {
                bat '''
                    "%PYTHON%" scripts/gerar_dados_inovaapps.py
                '''
            }
        }

        stage('Gerar pesos de alerta') {
            steps {
                bat '''
                    "%PYTHON%" scripts/gerar_pesos_alerta.py
                '''
            }
        }
    }
}