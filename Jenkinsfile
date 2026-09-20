pipeline {
    agent any

    stages {
        stage('Verificar ambiente') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            echo "===== USUARIO DO JENKINS ====="
                            whoami

                            echo "===== VERSAO DO PYTHON ====="
                            python3 --version || python --version

                            echo "===== DIRETORIO DO WORKSPACE ====="
                            pwd

                            echo "===== ARQUIVOS DO PROJETO ====="
                            ls -la
                        '''
                    } else {
                        bat '''
                            echo ===== USUARIO DO JENKINS =====
                            whoami

                            echo ===== VERSAO DO PYTHON =====
                            python --version

                            echo ===== DIRETORIO DO WORKSPACE =====
                            cd

                            echo ===== ARQUIVOS DO PROJETO =====
                            dir
                        '''
                    }
                }
            }
        }

        stage('Instalar dependencias') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            if command -v python3 >/dev/null 2>&1; then
                                python3 -m pip install -r requirements.txt
                            else
                                python -m pip install -r requirements.txt
                            fi
                        '''
                    } else {
                        bat '''
                            python -m pip install -r requirements.txt
                        '''
                    }
                }
            }
        }

        stage('Atualizar banco Holder') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            if command -v python3 >/dev/null 2>&1; then
                                python3 -m holder.infra.etl.ingestao
                            else
                                python -m holder.infra.etl.ingestao
                            fi
                        '''
                    } else {
                        bat '''
                            python -m holder.infra.etl.ingestao
                        '''
                    }
                }
            }
        }

        stage('Treinar modelo de risco') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            if command -v python3 >/dev/null 2>&1; then
                                python3 -m holder.aplicacao.treino
                            else
                                python -m holder.aplicacao.treino
                            fi
                        '''
                    } else {
                        bat '''
                            python -m holder.aplicacao.treino
                        '''
                    }
                }
            }
        }

        stage('Gerar dados do InovaApps') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            if command -v python3 >/dev/null 2>&1; then
                                python3 scripts/gerar_dados_inovaapps.py
                            else
                                python scripts/gerar_dados_inovaapps.py
                            fi
                        '''
                    } else {
                        bat '''
                            python scripts/gerar_dados_inovaapps.py
                        '''
                    }
                }
            }
        }

        stage('Gerar pesos dos alertas') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            if command -v python3 >/dev/null 2>&1; then
                                python3 scripts/gerar_pesos_alerta.py
                            else
                                python scripts/gerar_pesos_alerta.py
                            fi
                        '''
                    } else {
                        bat '''
                            python scripts/gerar_pesos_alerta.py
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline executada com sucesso.'
        }

        failure {
            echo 'Falha em alguma etapa da pipeline.'
        }

        always {
            echo 'Pipeline finalizada.'
        }
    }
}