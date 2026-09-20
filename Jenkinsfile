pipeline {
    agent any

    environment {
        PYTHON = 'C:\\Users\\tiago\\AppData\\Local\\Python\\bin\\python.exe'
        PROJETO = 'C:\\Users\\tiago\\OneDrive\\Ambiente de Trabalho\\Holder\\Holder'
    }

    stages {
        stage('Verificar ambiente') {
            steps {
                bat '''
                    echo ===== USUARIO DO JENKINS =====
                    whoami

                    echo ===== NOME DO COMPUTADOR =====
                    hostname

                    echo ===== VERSAO DO PYTHON =====
                    "%PYTHON%" --version

                    echo ===== PASTA DO PROJETO =====
                    if not exist "%PROJETO%" (
                        echo ERRO: pasta do projeto nao encontrada.
                        exit /b 1
                    )

                    cd /d "%PROJETO%"

                    echo ===== ARQUIVOS DO PROJETO =====
                    dir
                '''
            }
        }

        stage('Instalar dependencias') {
            steps {
                bat '''
                    cd /d "%PROJETO%"
                    "%PYTHON%" -m pip install -r requirements.txt
                '''
            }
        }

        stage('Atualizar banco Holder') {
            steps {
                bat '''
                    cd /d "%PROJETO%"
                    "%PYTHON%" -m holder.infra.etl.ingestao
                '''
            }
        }

        stage('Treinar modelo de risco') {
            steps {
                bat '''
                    cd /d "%PROJETO%"
                    "%PYTHON%" -m holder.aplicacao.treino
                '''
            }
        }

        stage('Gerar dados do InovaApps') {
            steps {
                bat '''
                    cd /d "%PROJETO%"
                    "%PYTHON%" scripts/gerar_dados_inovaapps.py
                '''
            }
        }

        stage('Gerar pesos dos alertas') {
            steps {
                bat '''
                    cd /d "%PROJETO%"
                    "%PYTHON%" scripts/gerar_pesos_alerta.py
                '''
            }
        }
    }

    post {
        success {
            echo 'Atualizacao, treinamento e geracao dos dados concluídos com sucesso.'
        }

        failure {
            echo 'Falha em alguma etapa da pipeline.'
        }

        always {
            echo 'Pipeline finalizado.'
        }
    }
}