/* users subscribed that are clients in the bank will never get an answer
   this query list them
 */
SELECT cached_results.user_id, users.rut, cached_results.rut, result
FROM cached_results INNER JOIN subscribed_users ON cached_results.user_id = subscribed_users.user_id
INNER JOIN users ON cached_results.rut = users.rut AND users.id = cached_results.user_id
WHERE cached_results.result LIKE "Eres cliente%";
