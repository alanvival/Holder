pipeline {
    agent any

    stages {

        stage('Localizar Python') {
            steps {
                script {
                    def pythonPath = bat(
                        script: '''
                            @echo off
                            setlocal EnableDelayedExpansion

                            echo ===== PROCURANDO PYTHON =====

                            rem 1. Verifica se o Python esta disponivel no PATH
                            for /f "delims=" %%P in ('where python 2^>nul') do (
                                echo %%P
                                exit /b 0
                            )

                            rem 2. Procura em todos os usuarios do Windows
                            for /d %%U in ("C:\\Users\\*") do (

                                rem Instalacao tradicional do Python
                                for /d %%V in ("%%~U\\AppData\\Local\\Programs\\Python\\Python*") do (
                                    if exist "%%~V\\python.exe" (
                                        echo %%~V\\python.exe
                                        exit /b 0
                                    )
                                )

                                rem Instalacao alternativa
                                if exist "%%~U\\AppData\\Local\\Python\\bin\\python.exe" (
                                    echo %%~U\\AppData\\Local\\Python\\bin\\python.exe
                                    exit /b 0
                                )
                            )

                            rem 3. Procura instalacoes na raiz do disco C:
                            for /d %%V in ("C:\\Python*") do (
                                if exist "%%~V\\python.exe" (
                                    echo %%~V\\python.exe
                                    exit /b 0
                                )
                            )

                            rem 4. Verifica caminhos comuns adicionais
                            if exist "C:\\Program Files\\Python313\\python.exe" (
                                echo C:\\Program Files\\Python313\\python.exe
                                exit /b 0
                            )

                            if exist "C:\\Program Files\\Python312\\python.exe" (
                                echo C:\\Program Files\\Python312\\python.exe
                                exit /b 0
                            )

                            if exist "C:\\Program Files\\Python311\\python.exe" (
                                echo C:\\Program Files\\Python311\\python.exe
                                exit /b 0
                            )

                            echo Python nao encontrado
                            exit /b 1
                        ''',
                        returnStdout: true
                    ).trim()

                    def linhas = pythonPath.readLines()
                    env.PYTHON = linhas.last().trim()

                    echo "Python encontrado em: ${env.PYTHON}"
                }
            }
        }

        stage('Verificar Python') {
            steps {
                bat '''
                    echo ===== VERSAO DO PYTHON =====
                    "%PYTHON%" --version

                    echo ===== VERSAO DO PIP =====
                    "%PYTHON%" -m pip --version
                '''
            }
        }

        stage('Instalar dependências') {
            steps {
                bat '''
                    echo ===== INSTALANDO DEPENDENCIAS =====
                    "%PYTHON%" -m pip install -r requirements.txt
                '''
            }
        }

        stage('Atualizar banco de dados') {
            steps {
                bat '''
                    echo ===== ATUALIZANDO BANCO DE DADOS =====
                    "%PYTHON%" -m holder.infra.etl.ingestao
                '''
            }
        }

        stage('Treinar modelo') {
            steps {
                bat '''
                    echo ===== TREINANDO MODELO =====
                    "%PYTHON%" -m holder.aplicacao.treino
                '''
            }
        }

        stage('Gerar dados InovaApps') {
            steps {
                bat '''
                    echo ===== GERANDO DADOS INOVAAPPS =====
                    "%PYTHON%" scripts/gerar_dados_inovaapps.py
                '''
            }
        }

        stage('Gerar pesos de alerta') {
            steps {
                bat '''
                    echo ===== GERANDO PESOS DE ALERTA =====
                    "%PYTHON%" scripts/gerar_pesos_alerta.py
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline executada com sucesso.'
        }

        failure {
            echo 'A pipeline falhou. Verifique os logs do Jenkins.'
        }
    }
}