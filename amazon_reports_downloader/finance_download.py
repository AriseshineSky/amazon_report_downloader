class FinanceDownload(object):
    def go_to_finance_download_page(self):
        try:
            # 移动鼠标到reports
            for i in range(0, 8):
                click = 'false'
                try:
                    reports = WebDriverWait(self.driver, 940, 0.5).until(
                        EC.presence_of_element_located((By.ID, 'sc-navtab-reports')))
                    time.sleep(random.randint(4, 7))
                    webdriver.ActionChains(self.driver).move_to_element(reports).perform()

                    logger.info('go to reports')
                    js_change_display = 'document.querySelector("#sc-navtab-reports > ul").style.display = "block";'
                    js_change_opacity = 'document.querySelector("#sc-navtab-reports > ul").style.opacity = 1;'
                    self.driver.execute_script(js_change_display)
                    self.driver.execute_script(js_change_opacity)
                    # click payments
                    try:
                        logger.info('click Payments')
                        fulfillment_link = self.driver.find_element_by_xpath(
                            '//*[@id="sc-navtab-reports"]/ul/li/a[contains(text(), "Payments")]').get_attribute(
                            'href')
                        self.driver.get(fulfillment_link)
                        break
                    except Exception as e:
                        print(e)


                    # length = len(self.driver.find_elements_by_xpath('//*[@id="sc-navtab-reports"]/ul/li'))
                    # logger.info(length)
                    # for i in range(1, length):
                    #     logger.info(('//*[@id="sc-navtab-reports"]/ul/li[{}]'.format(i)))
                    #     report_name = self.driver.find_element_by_xpath(
                    #         '//*[@id="sc-navtab-reports"]/ul/li[{}]'.format(i)).text.strip()
                    #     if report_name == 'Payments':
                    #         time.sleep(random.randint(3, 7))
                    #         js_click_payments = "document.querySelector('#sc-navtab-reports > ul > li:nth-child({}) > a').click();".format(
                    #             i)
                    #         self.driver.execute_script(js_click_payments)
                    #         logger.info('click payments')
                    #         time.sleep(random.randint(1, 7))
                    #         click = 'true'
                    #         break
                    # if click == 'true':
                    #     break

                except Exception as e:
                    print(e)


            # click data range report
            try:
                WebDriverWait(self.driver, 10, 0.5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'kat-tab-header[tab-id="DATE_RANGE_REPORTS"]')))
                # for k in range(3, 6):
                #     logger.info('#root > div > article > section kat-tab-pane > kat-tab-header:nth-child({}) > div > span.katal-tab-label > span'.format(k))
                #     tab_name = self.driver.find_element_by_css_selector('#root > div > article > section kat-tab-pane > kat-tab-header:nth-child({}) > div > span.katal-tab-label > span'.format(k)).text.strip()
                #     if tab_name == "Date Range Reports":
                script = 'document.querySelector("kat-tab-header[tab-id=DATE_RANGE_REPORTS]").click();'
                self.driver.execute_script(script)
            except Exception as e:
                print(e)
            logger.info('click data range report')
            time.sleep(random.randint(4, 7))

            # click generate report

            WebDriverWait(self.driver, 940, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#drrGenerateReportButton')))
            script = 'document.querySelector("#drrGenerateReportButton").click();'
            self.driver.execute_script(script)

            logger.info('click data range report')
            time.sleep(random.randint(4, 7))

            # select date

            start = WebDriverWait(self.driver, 940, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#drrFromDate')))
            start.click()
            seven_days_ago = (datetime.utcnow().date() - timedelta(days=random.randint(7, 10))).strftime("%m/%d/%Y")
            start.send_keys(seven_days_ago)
            time.sleep(random.randint(3, 7))
            end = WebDriverWait(self.driver, 940, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#drrToDate')))
            end.click()
            yesterday = (datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-7))) - timedelta(days=1)).strftime("%m/%d/%Y")
            end.send_keys(yesterday)

            logger.info('select date')
            time.sleep(random.randint(4, 7))

            # generate

            WebDriverWait(self.driver, 940, 0.5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#drrGenerateReportsGenerateButton')))
            script = 'document.querySelector("#drrGenerateReportsGenerateButton").click();'
            self.driver.execute_script(script)

            logger.info('select date')
            time.sleep(random.randint(10, 20))
            self.scroll_down()
            self.driver.refresh()
            time.sleep(random.randint(20, 30))
            # click download

            download_button = WebDriverWait(self.driver, 900, 0.5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="downloadButton"]/span/a')))
            logger.info('click download')
            time.sleep(random.randint(4, 7))
            download_link = download_button.get_attribute("href")
            self.driver.get(download_link)
            bulk_report = re.findall(r"fileName=(.*)?\.csv", download_link)[0]
            logger.info(bulk_report)
            time.sleep(random.randint(10, 20))
            return bulk_report + '.csv'
        except Exception as e:
            self.save_page(traceback.format_exc())
            print(e)
            self.driver.quit()